import azure.functions as func

from blocker_doc_and_solution_bot.search_api.app import app as fastapi_app

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
