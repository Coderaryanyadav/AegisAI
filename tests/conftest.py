import os
import sys
# Python 3.14 compatibility workaround for protobuf custom tp_new crash
sys.modules['google._upb._message'] = None

os.environ["DATABASE_URL"] = "sqlite:///tests/test_aegis_ai.db"
os.environ["AEGIS_TEST_MODE"] = "true"

