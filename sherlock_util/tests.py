from sherlock_master.sherlock_utils import get_detailed_results_async
import asyncio
import json

result = asyncio.run(get_detailed_results_async('johndoe'))
print(json.dumps(result, indent=2))