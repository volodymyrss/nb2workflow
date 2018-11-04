from __future__ import print_function

import os
import argparse
import docker
import shutil
import tempfile
import checksumdir
 
def build_python(dockefile):
    dockerfile.append("RUN yum install -y python")
    dockerfile.append("RUN curl https://bootstrap.pypa.io/get-pip.py | python")

def import_repo(repo_source,target):
    print("importing repo",repo_source,"to",target)
    if os.path.isdir(repo_source):
        shutil.copytree(repo_source, target)
    else:
        raise NotImplementedError

    return checksumdir.dirhash(target)

def build_image(repo_source,from_image,tag_image):
    tempdir=tempfile.mkdtemp()

    rel_repo_path="repo"
    repo_path=os.path.join(tempdir,rel_repo_path)

    repo_hash=import_repo(repo_source,repo_path)
    
    dockerfile=[]

    dockerfile.append("FROM {}".format(from_image))
    dockerfile.append("RUN git clone https://github.com/volodymyrss/nb2workflow.git /nb2workflow; cd /nb2workflow; git reset --hard 0d8b4cc; pip install -r requirements.txt; pip install .") # arg it
    dockerfile.append("ADD ./{} /repo".format(rel_repo_path))
    dockerfile.append("RUN touch /repo-hash-{}; pip install -r /repo/requirements.txt".format(repo_hash))
    dockerfile.append("WORKDIR /workdir")

    open(os.path.join(tempdir,"Dockerfile"),"w").write(("\n".join(dockerfile))+"\n")

    cli=docker.from_env()
    
    print("building image, tagging as",tag_image)
    return cli.images.build(
                    path=tempdir,
                    tag=tag_image,
                    quiet=False,
                )

def main():

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('repo', metavar='repo', type=str)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--name', metavar='TAG', type=str, default="nb2worker")
    parser.add_argument('--from-image', metavar='FROM IMAGE', type=str, default="python:2.7")
    parser.add_argument('--tag-image', metavar='TAG', type=str, default="")
    parser.add_argument('--host', metavar='host', type=str, default="127.0.0.1")
    parser.add_argument('--port', metavar='port', type=int, default=9191)

    args = parser.parse_args()

    repo_path=args.repo
    tag_image=args.tag_image

    if args.tag_image == "":
        tag_image=os.path.basename(os.path.abspath(repo_path))

    build_result=build_image(repo_path,args.from_image,tag_image)

    if build_result is None:
        raise Exception("failed to build")

    print("built:",build_result)
    #print("\n".join(list(build_result[1])))

    if args.run:
        
        print("running",tag_image,"service on",args.port)
        cli=docker.from_env()
        cli.containers.run(
            tag_image,
            user=os.getuid(),
            ports={ 9191: (args.host, args.port) },
            command="nb2service /repo/ --host 0.0.0.0", 
            name=args.name,
            volumes={os.getcwd():{"bind":"/workdir","mode":"rw"}},
            auto_remove=True,
        )

if __name__=="__main__":
    main()