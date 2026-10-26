import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from agent_runner import ask_agent


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


if __name__ == "__main__":
    unittest.main()
