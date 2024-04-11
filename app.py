from flask import Flask

app = Flask(__name__)

@app.route("/",methods=["GET"])
def root():
    return "Hello Flask"


if __name__ == "__main__":
    app.run(port=5000,debug=True)