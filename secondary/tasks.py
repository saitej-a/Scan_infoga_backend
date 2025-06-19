from celery import shared_task
from .utils import fetch_payworld_data, fetch_razorpay_ifsc_data
from .models import PayworldData2, RazorpayIFSCData

@shared_task
def fetch_and_store_payworld_data(sender_mobile, api_response):
    try:
        if api_response.get("message") == "Sender is not registered":
            return {"status": False, "message": api_response["message"]}

        new_data = api_response["data"]
        timestamp = new_data.pop("datetime")
        new_data_dict = {timestamp: new_data}

        obj, _ = PayworldData2.objects.get_or_create(sender_mobile_number=sender_mobile)
        existing = obj.result or []
        print("Existing: ",existing)
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


@shared_task
def fetch_and_store_razorpay_data(ifsc_code, api_response):
    try:
        new_data = api_response["data"]
        timestamp = new_data.pop("datetime")
        new_data_dict = {timestamp: new_data}
        
        obj, _ = RazorpayIFSCData.objects.get_or_create(ifsc_code=ifsc_code)
        existing = obj.result or {}
        print("Existing: ",existing)
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