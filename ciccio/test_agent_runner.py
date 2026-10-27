import io
import json
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from agent_runner import ask_agent, collect_task_sources, execute_read_with_retry, failed_task_attempts, groq_completion_with_retry, is_transient_error, record_failure, notify_telegram, task_requires_market_evidence, task_search_queries


def fake_groq_response(text):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )
    return client


class AskAgentValidationTests(unittest.TestCase):
    def test_incomplete_model_plan_falls_back_to_no_op(self):
        groq = fake_groq_response(json.dumps({
            "goal": "Migliorare Ciccio",
            "action_type": "create_task",
        }))
        plan = ask_agent(groq, [], [], [])
        self.assertEqual(plan["action_type"], "no_op")
        self.assertIn("incompleta", plan["reason"].lower())
        self.assertTrue(plan["action_notes"])

    def test_unknown_action_falls_back_to_no_op(self):
        plan_data = {
            "goal": "Verificare il progetto",
            "action_type": "delete_repository",
            "action_title": "Eliminare il progetto",
            "action_notes": "Azione non consentita",
            "reason": "Test",
            "expected_result": "Test",
            "verification": "Test",
            "learning": "Test",
            "next_cycle": "Test",
        }
        plan = ask_agent(fake_groq_response(json.dumps(plan_data)), [], [], [])
        self.assertEqual(plan["action_type"], "no_op")
        self.assertIn("non valido", plan["action_notes"].lower())

    def test_model_cannot_mark_task_complete_without_runner_verification(self):
        plan_data = {
            "goal": "Completare un'attività",
            "action_type": "complete_task",
            "action_title": "Attività da fare",
            "action_notes": "Dico che è completata",
            "reason": "Test",
            "expected_result": "Completata",
            "verification": "Risultato verificato",
            "learning": "Non fidarsi di affermazioni senza prova",
            "next_cycle": "Verificare il deliverable",
        }
        plan = ask_agent(fake_groq_response(json.dumps(plan_data)), [], [], [])
        self.assertEqual(plan["action_type"], "no_op")
        self.assertIn("non valido", plan["action_notes"].lower())

    def test_valid_internal_action_is_preserved(self):
        plan_data = {
            "goal": "Creare una piccola attività",
            "action_type": "create_task",
            "action_title": "Verificare gli annunci salvati",
            "action_notes": "Controllare i dati di esempio",
            "reason": "Migliora la qualità",
            "expected_result": "Controllo registrato",
            "verification": "Verificare il record in Supabase",
            "learning": "Preferire controlli misurabili",
            "next_cycle": "Rileggere il risultato",
            "memory_kind": "apprendimento_agente",
            "memory_content": "",
        }
        plan = ask_agent(fake_groq_response(json.dumps(plan_data)), [], [], [])
        self.assertEqual(plan["action_type"], "create_task")
        self.assertEqual(plan["action_title"], "Verificare gli annunci salvati")


class GroqRetryTests(unittest.TestCase):
    def test_transient_connection_error_is_retried(self):
        groq = Mock()
        expected = object()
        groq.chat.completions.create.side_effect = [ConnectionError("temporary network issue"), expected]
        with patch("agent_runner.time.sleep") as sleep:
            result = groq_completion_with_retry(groq, model="test", messages=[])
        self.assertIs(result, expected)
        self.assertEqual(groq.chat.completions.create.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_non_transient_error_is_not_retried(self):
        groq = Mock()
        groq.chat.completions.create.side_effect = ValueError("invalid request")
        with patch("agent_runner.time.sleep") as sleep:
            with self.assertRaises(ValueError):
                groq_completion_with_retry(groq, model="test", messages=[])
        self.assertEqual(groq.chat.completions.create.call_count, 1)
        sleep.assert_not_called()




class SupabaseReadRetryTests(unittest.TestCase):
    def test_transient_read_error_is_retried(self):
        query = Mock()
        expected = SimpleNamespace(data=[{"id": "1"}])
        query.execute.side_effect = [TimeoutError("temporary timeout"), expected]
        with patch("agent_runner.time.sleep") as sleep:
            result = execute_read_with_retry(query)
        self.assertIs(result, expected)
        self.assertEqual(query.execute.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_read_error_is_not_retried_when_permanent(self):
        query = Mock()
        query.execute.side_effect = ValueError("bad query")
        with patch("agent_runner.time.sleep") as sleep:
            with self.assertRaises(ValueError):
                execute_read_with_retry(query)
        self.assertEqual(query.execute.call_count, 1)
        sleep.assert_not_called()



class FailureLoggingTests(unittest.TestCase):
    def test_failure_record_uses_failed_status(self):
        db = Mock()
        db.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[{"id": "run-1"}]
        )
        ok = record_failure(
            db,
            "esecuzione azione",
            RuntimeError("test failure"),
            {"goal": "Test Ciccio", "action_type": "create_task", "action_title": "Test task"},
        )
        self.assertTrue(ok)
        inserted_row = db.table.return_value.insert.call_args.args[0]
        self.assertEqual(inserted_row["status"], "failed")
        self.assertIn("esecuzione azione", inserted_row["reason"])
        self.assertIn("test failure", inserted_row["result"])

    def test_failure_logging_does_not_mask_database_error(self):
        db = Mock()
        db.table.return_value.insert.return_value.execute.side_effect = RuntimeError("database offline")
        self.assertFalse(record_failure(db, "lettura", RuntimeError("original error")))
        
    def test_transient_classifier(self):
        self.assertTrue(is_transient_error(TimeoutError("timeout")))
        self.assertTrue(is_transient_error(ConnectionError("connection reset")))
        self.assertFalse(is_transient_error(ValueError("invalid input")))



class FailedTaskAttemptTests(unittest.TestCase):
    def test_counts_only_failures_since_last_task_update(self):
        task = {
            "title": "Generare annuncio",
            "updated_at": "2026-10-26T10:00:00+00:00",
        }
        history = [
            {"created_at": "2026-10-26T09:00:00+00:00", "status": "failed",
             "action": "execute_task: Generare annuncio"},
            {"created_at": "2026-10-26T11:00:00+00:00", "status": "blocked",
             "action": "execute_task: Generare annuncio — output breve"},
            {"created_at": "2026-10-26T12:00:00+00:00", "status": "failed",
             "action": "execute_task: Generare annuncio — timeout"},
            {"created_at": "2026-10-26T13:00:00+00:00", "status": "completed",
             "action": "execute_task: Generare annuncio"},
        ]
        self.assertEqual(failed_task_attempts(task, history), 2)

    def test_manual_task_update_resets_failure_window(self):
        task = {
            "title": "Generare annuncio",
            "updated_at": "2026-10-26T14:00:00+00:00",
        }
        history = [
            {"created_at": "2026-10-26T11:00:00+00:00", "status": "failed",
             "action": "execute_task: Generare annuncio"},
            {"created_at": "2026-10-26T12:00:00+00:00", "status": "blocked",
             "action": "execute_task: Generare annuncio"},
            {"created_at": "2026-10-26T13:00:00+00:00", "status": "failed",
             "action": "execute_task: Generare annuncio"},
        ]
        self.assertEqual(failed_task_attempts(task, history), 0)


class MarketResearchGuardrailTests(unittest.TestCase):
    def test_market_validation_uses_several_targeted_queries(self):
        queries = task_search_queries(
            "Validazione mercato — servizio contenuti LinkedIn",
            "Verifica domanda, prezzi e concorrenti in Italia",
        )
        self.assertGreaterEqual(len(queries), 3)
        self.assertTrue(any("LinkedIn" in query or "linkedin" in query for query in queries))

    def test_market_validation_requires_evidence(self):
        self.assertTrue(task_requires_market_evidence(
            "Validazione mercato — servizio contenuti LinkedIn",
            "Verifica la domanda e i prezzi pubblici",
        ))
        self.assertFalse(task_requires_market_evidence(
            "Campione vendibile — 5 post LinkedIn",
            "Scrivi cinque esempi pronti da consegnare",
        ))

    def test_collect_sources_deduplicates_real_urls(self):
        from unittest.mock import patch
        with patch("agent_runner.search_web", side_effect=[
            [{"title": "Fonte A", "url": "https://example.com/a", "snippet": "Prezzi pubblici"}],
            [{"title": "Fonte A duplicata", "url": "https://example.com/a", "snippet": "Duplicato"},
             {"title": "Fonte B", "url": "https://example.com/b", "snippet": "Offerta pubblica"}],
            [],
        ]):
            sources = collect_task_sources(
                "Validazione mercato — servizio contenuti LinkedIn",
                "Verifica domanda",
                max_results=5,
            )
        self.assertEqual([item["url"] for item in sources], [
            "https://example.com/a", "https://example.com/b"
        ])


class TelegramNotificationTests(unittest.TestCase):
    def test_telegram_is_optional_without_credentials(self):
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            self.assertFalse(notify_telegram("test message"))

    def test_telegram_token_is_redacted_from_errors(self):
        token = "123456:secret-token"
        output = io.StringIO()
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": "123"}):
            with patch("urllib.request.urlopen", side_effect=RuntimeError("failed URL https://api.telegram.org/bot" + token + "/sendMessage")):
                with redirect_stdout(output):
                    self.assertFalse(notify_telegram("test message"))
        self.assertNotIn(token, output.getvalue())
        self.assertIn("[REDACTED]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
