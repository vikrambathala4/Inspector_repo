FROM alpine:edge
 
RUN apk add python3 aws-cli 

COPY ./entrypoint . 
RUN chmod 0500 /main.py

ENTRYPOINT ["/main.py"]

# note: don't set a WORKDIR in this image, it conflicts with github actions:
# https://docs.github.com/en/actions/creating-actions/dockerfile-support-for-github-actions#workdir
