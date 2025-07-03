import datetime
import trio
import httpx
import time
import re
import importlib
import pkgutil

from holehe_tool.core import import_submodules, get_functions, is_email



async def check_email_on_sites(email, timeout=10, only_used=False, no_password_recovery=False):
    """
    API function to check if an email is registered on various websites
    
    Args:
        email (str): The email to check
        timeout (int): Request timeout in seconds
        only_used (bool): If True, only return sites where the email is used
        no_password_recovery (bool): If True, skip password recovery checks
        
    Returns:
        list: List of dictionaries with results for each website
    """
    # Validate email format
    if not is_email(email):
        raise ValueError("Invalid email format")
    
    # Create a class to mimic args for get_functions
    class Args:
        def __init__(self):
            self.nopasswordrecovery = no_password_recovery
    
    args = Args()
    
    # Import modules and get functions
    modules = import_submodules("holehe.modules")
    websites = get_functions(modules, args)
    
    # Start time for tracking
    start_time = time.time()
    
    # Create async client
    client = httpx.AsyncClient(timeout=timeout)
    
    # Results list
    results = []
    
    # Define the launch_module function
    async def launch_module(module, email, client, out):
        data = {'aboutme': 'about.me', 'adobe': 'adobe.com', 'amazon': 'amazon.com', 'anydo': 'any.do', 'archive': 'archive.org', 'armurerieauxerre': 'armurerie-auxerre.com', 'atlassian': 'atlassian.com', 'babeshows': 'babeshows.co.uk', 'badeggsonline': 'badeggsonline.com', 'biosmods': 'bios-mods.com', 'biotechnologyforums': 'biotechnologyforums.com', 'bitmoji': 'bitmoji.com', 'blablacar': 'blablacar.com', 'blackworldforum': 'blackworldforum.com', 'blip': 'blip.fm', 'blitzortung': 'forum.blitzortung.org', 'bluegrassrivals': 'bluegrassrivals.com', 'bodybuilding': 'bodybuilding.com', 'buymeacoffee': 'buymeacoffee.com', 'cambridgemt': 'discussion.cambridge-mt.com', 'caringbridge': 'caringbridge.org', 'chinaphonearena': 'chinaphonearena.com', 'clashfarmer': 'clashfarmer.com', 'codecademy': 'codecademy.com', 'codeigniter': 'forum.codeigniter.com', 'codepen': 'codepen.io', 'coroflot': 'coroflot.com', 'cpaelites': 'cpaelites.com', 'cpahero': 'cpahero.com', 'cracked_to': 'cracked.to', 'crevado': 'crevado.com', 'deliveroo': 'deliveroo.com', 'demonforums': 'demonforums.net', 'devrant': 'devrant.com', 'diigo': 'diigo.com', 'discord': 'discord.com', 'docker': 'docker.com', 'dominosfr': 'dominos.fr', 'ebay': 'ebay.com', 'ello': 'ello.co', 'envato': 'envato.com', 'eventbrite': 'eventbrite.com', 'evernote': 'evernote.com', 'fanpop': 'fanpop.com', 'firefox': 'firefox.com', 'flickr': 'flickr.com', 'freelancer': 'freelancer.com', 'freiberg': 'drachenhort.user.stunet.tu-freiberg.de', 'garmin': 'garmin.com', 'github': 'github.com', 'google': 'google.com', 'gravatar': 'gravatar.com', 'imgur': 'imgur.com', 'instagram': 'instagram.com', 'issuu': 'issuu.com', 'koditv': 'forum.kodi.tv', 'komoot': 'komoot.com', 'laposte': 'laposte.fr', 'lastfm': 'last.fm', 'lastpass': 'lastpass.com', 'mail_ru': 'mail.ru', 'mybb': 'community.mybb.com', 'myspace': 'myspace.com', 'nattyornot': 'nattyornotforum.nattyornot.com', 'naturabuy': 'naturabuy.fr', 'ndemiccreations': 'forum.ndemiccreations.com', 'nextpvr': 'forums.nextpvr.com', 'nike': 'nike.com', 'odnoklassniki': 'ok.ru', 'office365': 'office365.com', 'onlinesequencer': 'onlinesequencer.net', 'parler': 'parler.com', 'patreon': 'patreon.com', 'pinterest': 'pinterest.com', 'plurk': 'plurk.com', 'pornhub': 'pornhub.com', 'protonmail': 'protonmail.ch', 'quora': 'quora.com', 'rambler': 'rambler.ru', 'redtube': 'redtube.com', 'replit': 'replit.com', 'rocketreach': 'rocketreach.co', 'samsung': 'samsung.com', 'seoclerks': 'seoclerks.com', 'sevencups': '7cups.com', 'smule': 'smule.com', 'snapchat': 'snapchat.com', 'soundcloud': 'soundcloud.com', 'sporcle': 'sporcle.com', 'spotify': 'spotify.com', 'strava': 'strava.com', 'taringa': 'taringa.net', 'teamtreehouse': 'teamtreehouse.com', 'tellonym': 'tellonym.me', 'thecardboard': 'thecardboard.org', 'therianguide': 'forums.therian-guide.com', 'thevapingforum': 'thevapingforum.com', 'tumblr': 'tumblr.com', 'tunefind': 'tunefind.com', 'twitter': 'twitter.com', 'venmo': 'venmo.com', 'vivino': 'vivino.com', 'voxmedia': 'voxmedia.com', 'vrbo': 'vrbo.com', 'vsco': 'vsco.co', 'wattpad': 'wattpad.com', 'wordpress': 'wordpress.com', 'xing': 'xing.com', 'xnxx': 'xnxx.com', 'xvideos': 'xvideos.com', 'yahoo': 'yahoo.com','hubspot': 'hubspot.com', 'pipedrive': 'pipedrive.com', 'insightly': 'insightly.com', 'nutshell': 'nutshell.com', 'zoho': 'zoho.com', 'axonaut': 'axonaut.com', 'amocrm': 'amocrm.com', 'nimble': 'nimble.com', 'nocrm': 'nocrm.io', 'teamleader': 'teamleader.eu'}
        try:
            await module(email, client, out)
        except Exception:
            name = str(module).split('<function ')[1].split(' ')[0]
            out.append({"name": name, "domain": data.get(name, "unknown"),
                        "rateLimit": False,
                        "error": True,
                        "exists": False,
                        "emailrecovery": None,
                        "phoneNumber": None,
                        "others": None})
    
    # Run all modules concurrently
    async with trio.open_nursery() as nursery:
        for website in websites:
            nursery.start_soon(launch_module, website, email, client, results)
    
    # Close the client
    await client.aclose()
    
    # Filter results if only_used is True
    if only_used:
        results = [r for r in results if r.get("exists", False)]
    
    # Sort results by name
    results = sorted(results, key=lambda i: i['name'])
    
    # Add execution time metadata
    execution_time = time.time() - start_time
    metadata = {
        "email": email,
        "websites_checked": len(websites),
        "execution_time": round(execution_time, 2),
    }
    
    return {"results": results, "metadata": metadata, "datetime": datetime.datetime.now().isoformat() + "Z"}


def check_email(email, timeout=10, only_used=False, no_password_recovery=False):
    """
    Synchronous wrapper for the async check_email_on_sites function
    
    Args:
        email (str): The email to check
        timeout (int): Request timeout in seconds
        only_used (bool): If True, only return sites where the email is used
        no_password_recovery (bool): If True, skip password recovery checks
        
    Returns:
        list: List of dictionaries with results for each website
    """
    return trio.run(check_email_on_sites, email, timeout, only_used, no_password_recovery)
