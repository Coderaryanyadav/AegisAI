import os
os.environ["DATABASE_URL"] = "sqlite:///tests/test_aegis_ai.db"
os.environ["AEGIS_TEST_MODE"] = "true"
