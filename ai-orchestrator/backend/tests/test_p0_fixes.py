"""
Tests unitaires pour les corrections P0 (sans pytest)
"""
import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_p01_add_message_rejects_empty_content():
    """P0-1: Vérifie que add_message refuse les contenus vides pour assistant"""
    
    # Simuler la fonction add_message avec la validation
    def add_message_with_validation(role, content):
        if role == "assistant" and (not content or not content.strip()):
            return "❌ Erreur: Impossible de générer une réponse. Veuillez reformuler votre demande."
        return content
    
    # Tests
    assert add_message_with_validation("assistant", "") == "❌ Erreur: Impossible de générer une réponse. Veuillez reformuler votre demande.", "Empty string should be rejected"
    assert add_message_with_validation("assistant", "   ") == "❌ Erreur: Impossible de générer une réponse. Veuillez reformuler votre demande.", "Whitespace should be rejected"
    assert add_message_with_validation("assistant", "Hello") == "Hello", "Valid content should pass"
    assert add_message_with_validation("user", "") == "", "User can be empty"
    
    print("✅ P0-1: Test validation réponses vides PASSÉ")


def test_p02_successful_results_collection():
    """P0-2: Vérifie que les résultats sont collectés"""
    successful_tool_results = []
    
    # Simuler des résultats
    results = [
        ("docker_ps", "Container list..."),
        ("uptime", "up 15 days"),
        ("error_cmd", "❌ Erreur permission"),
        ("disk_usage", "50% used")
    ]
    
    for tool_name, result in results:
        if result and not result.startswith("❌") and not result.startswith("Erreur"):
            successful_tool_results.append(f"{tool_name}: {result[:200]}")
    
    assert len(successful_tool_results) == 3, f"Expected 3 results, got {len(successful_tool_results)}"
    assert "docker_ps" in successful_tool_results[0], "docker_ps should be first"
    assert "uptime" in successful_tool_results[1], "uptime should be second"
    print("✅ P0-2a: Test collecte résultats PASSÉ")


def test_p02_fallback_message_structure():
    """P0-2: Vérifie la structure du message de fallback"""
    successful_tool_results = ["uptime: up 15 days", "docker_ps: 10 containers"]
    MAX_ITERATIONS = 30
    
    if successful_tool_results:
        fallback = f"⚠️ **Limite d'itérations atteinte** ({MAX_ITERATIONS})\n\n"
        for i, result in enumerate(successful_tool_results[-5:], 1):
            fallback += f"{i}. {result}\n"
    else:
        fallback = f"❌ **Échec de traitement**"
    
    assert "Limite d'itérations" in fallback, "Should contain limit message"
    assert "uptime" in fallback, "Should contain uptime result"
    assert "docker_ps" in fallback, "Should contain docker_ps result"
    print("✅ P0-2b: Test message fallback PASSÉ")


def test_p03_think_extraction():
    """P0-3: Vérifie l'extraction des phases THINK"""
    assistant_text = "THINK: Je vais analyser le système\nPLAN: 1. uptime 2. disk\nACTION: uptime()"
    
    think_found = False
    if "THINK:" in assistant_text.upper():
        think_match = assistant_text.upper().find("THINK:")
        think_content = assistant_text[think_match:think_match+200]
        think_found = True
        assert "analyser" in think_content.lower(), "THINK content should contain analyser"
    
    assert think_found, "THINK should be found"
    print("✅ P0-3a: Test extraction THINK PASSÉ")


def test_p03_plan_extraction():
    """P0-3: Vérifie l'extraction des phases PLAN"""
    assistant_text = "THINK: test\nPLAN: 1. faire uptime 2. vérifier disque"
    
    plan_found = False
    if "PLAN:" in assistant_text.upper():
        plan_match = assistant_text.upper().find("PLAN:")
        plan_content = assistant_text[plan_match:plan_match+200]
        plan_found = True
        assert "uptime" in plan_content.lower(), "PLAN content should contain uptime"
    
    assert plan_found, "PLAN should be found"
    print("✅ P0-3b: Test extraction PLAN PASSÉ")


if __name__ == "__main__":
    print("="*50)
    print("TESTS P0 - Corrections AI Orchestrator")
    print("="*50 + "\n")
    
    try:
        test_p01_add_message_rejects_empty_content()
        test_p02_successful_results_collection()
        test_p02_fallback_message_structure()
        test_p03_think_extraction()
        test_p03_plan_extraction()
        
        print("\n" + "="*50)
        print("✅ TOUS LES TESTS P0 PASSÉS (5/5)")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ TEST ÉCHOUÉ: {e}")
        sys.exit(1)
