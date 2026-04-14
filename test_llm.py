
from service.llm_client import call_llm

# Simple test to verify LLM integration is working. This is not a unit test, just a quick check.
print(call_llm("Explain housing demand factors without using numbers."))
