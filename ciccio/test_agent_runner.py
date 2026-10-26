import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent_runner import ask_agent, execute_read_with_retry, groq_completion_with_retry, is_transient_error, record_failure, notify_telegram


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



class TelegramNotificationTests(unittest.TestCase):
    def test_telegram_is_optional_without_credentials(self):
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            self.assertFalse(notify_telegram("test message"))


if __name__ == "__main__":
    unittest.main()
