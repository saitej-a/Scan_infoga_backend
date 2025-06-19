from celery import shared_task
from .models import UPIToAccount

@shared_task
def fetch_and_store_upi_to_account(upi_id, api_response):
    try:
        new_data = api_response["data"]
        timestamp = new_data.pop("datetime")
        new_data_dict = {timestamp: new_data}

        obj, _ = UPIToAccount.objects.get_or_create(upi_id=upi_id)
        existing = obj.result or {}

        def last_cleaned():
            if not existing:
                return None, None
            last_entry = existing[-1]
            last_timestamp = list(last_entry.keys())[0]
            return last_timestamp, last_entry[last_timestamp]

        last_ts, last_data = last_cleaned()

        if last_data != new_data:
            existing.append(new_data_dict)
            obj.result = existing
            obj.save()
            return {"status": True, "message": "New data appended"}
        else:
            return {"status": True, "message": "No change in data"}

    except Exception as e:
        import traceback
        return {"status": False, "message": str(e), "traceback": traceback.format_exc()}

        
        
        