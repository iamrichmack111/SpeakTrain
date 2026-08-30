import os

from speaktrain import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("SPEAKTRAIN_HOST", "0.0.0.0"),
        port=int(os.environ.get("SPEAKTRAIN_PORT", "8095")),
        debug=os.environ.get("SPEAKTRAIN_DEBUG", "0") == "1",
    )
