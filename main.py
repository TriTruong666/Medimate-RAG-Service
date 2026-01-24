import sys
import os
from fastapi import FastAPI
from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.common.interceptor import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    APIResponse,
)

sys.path.append(os.getcwd())


def print_banner():
    logo = r"""
███╗   ███╗███████╗██████╗ ██╗███╗   ███╗ █████╗ ████████╗███████╗
████╗ ████║██╔════╝██╔══██╗██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║█████╗  ██║  ██║██║██╔████╔██║███████║   ██║   █████╗  
██║╚██╔╝██║██╔══╝  ██║  ██║██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║███████╗██████╔╝██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

██████╗  █████╗  ██████╗     ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗
██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝
██████╔╝███████║██║  ███╗    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  
██╔══██╗██╔══██║██║   ██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  
██║  ██║██║  ██║╚██████╔╝    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝
    """
    print(logo)


def main():
    print_banner()
    # Khởi tạo fastapi
    app = FastAPI(title=f"Medimate RAG Services - {settings.AUTHOR_NAME}")

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.add_exception_handler(Exception, general_exception_handler)


if __name__ == "__main__":
    main()
