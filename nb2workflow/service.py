from __future__ import print_function

from flask import Flask, make_response, jsonify, request
from flask.json import JSONEncoder
from flask_caching import Cache


import os
import glob

from nb2workflow.nbadapter import NotebookAdapter, find_notebooks

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj, *args, **kwargs):
        try:
            if isinstance(obj, type):
                return dict(type_object=repr(obj))
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

cache = Cache(config={'CACHE_TYPE': 'simple'})

def create_app():
    app=Flask(__name__)
    app.json_encoder = CustomJSONEncoder
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})
    return app

app = create_app()


@app.route('/api/v1.0/get/<string:target>',methods=['GET'])
#@cache.cached(timeout=3600)
def workflow(target):
    issues = []

    nba = app.notebook_adapters.get(target)

    if nba is None:
        issues.append("target not known: %s; available targets: %s"%(target,app.notebook_adapters.keys()))
    else:
        interpreted_parameters = nba.interpret_parameters(request.args)
        issues += interpreted_parameters['issues']

    if len(issues)>0:
        return make_response(jsonify(issues=issues), 400)
    else:
        nba.execute(interpreted_parameters['request_parameters'])

        return jsonify(nba.extract_output())

# list input -> output function signatures and identities

@app.route('/api/v1.0/options',methods=['GET'])
def workflow_options():
    return jsonify(dict([
                    (target,dict(output=None,parameters=nba.extract_parameters()))
                     for target, nba in app.notebook_adapters.items()]))

@app.route('/health')
def healthcheck():
    issues=[]

    if len(issues)==0:
        return "all is ok!"
    else:
        return make_response(jsonify(issues=issues), 500)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('notebook', metavar='notebook', type=str)
    parser.add_argument('--host', metavar='host', type=str, default="127.0.0.1")
    parser.add_argument('--port', metavar='port', type=int, default=9191)
    #parser.add_argument('--tmpdir', metavar='tmpdir', type=str, default=None)

    args = parser.parse_args()

    app.notebook_adapters = find_notebooks(args.notebook)

    app.run(host=args.host,port=args.port)

if __name__ == '__main__':
    main()

