import azure.functions as func

from blocker_doc_and_solution_bot.search_api.app import app as fastapi_app

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(
    route="{*route}",
    methods=[
        func.HttpMethod.GET,
        func.HttpMethod.POST,
        func.HttpMethod.PUT,
        func.HttpMethod.DELETE,
        func.HttpMethod.PATCH,
        func.HttpMethod.HEAD,
        func.HttpMethod.OPTIONS,
    ],
    auth_level=func.AuthLevel.ANONYMOUS,
)
async def http_app_func(
    req: func.HttpRequest, context: func.Context
) -> func.HttpResponse:
    return await func.AsgiMiddleware(fastapi_app).handle_async(req, context)
