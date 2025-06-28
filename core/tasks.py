from celery import shared_task
from django import template
from core.services.email_service import EmailService
from secondary.models import PayworldData2, RazorpayIFSCData, PaynearbyData, RazorpayIFSCData2
from mobile.models import UPIToAccount, UPIToAccount2

@shared_task
def send_welcome_email(user_email, name):
    context = {
        "username": name,
        # "site_url": "http://scaninfoga.com"
    }
    print("shared task")
    email_sent = EmailService.send_email(template_name="welcome_template", to_email=user_email, context=context)
    
    if email_sent:
        return "Welcome email sent successfully"
    else:
        return "Failed to send welcome email"

@shared_task
def send_otp_email(user_email, name, otp, reset_password = False):
    context = {
        "username": name,
        "otp": otp,
    }
    print("shared task")
    template_name = "otp_template_reset_password"  if reset_password else "otp_template"
    email_sent = EmailService.send_email(template_name=template_name, to_email=user_email, context=context)
    
    if email_sent:
        return "OTP email sent successfully"
    else:
        return "Failed to send OTP email"


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
        
        obj, _ = RazorpayIFSCData2.objects.get_or_create(ifsc_code=ifsc_code)
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


@shared_task
def fetch_and_store_upi_to_account(upi_id, api_response):
    try:
        new_data = api_response["data"]
        timestamp = new_data.pop("datetime")
        new_data_dict = {timestamp: new_data}

        obj, _ = UPIToAccount2.objects.get_or_create(upi_id=upi_id)
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


@shared_task
def fetch_and_store_paynearby_data(mobile_number, api_response):
    try:
        new_data = api_response["data"]
        timestamp = new_data.pop("datetime")
        new_data_dict = {timestamp: new_data}

        obj, _ = PaynearbyData.objects.get_or_create(Mobile_number=mobile_number)
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
        