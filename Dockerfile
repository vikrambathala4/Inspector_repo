FROM alpine:latest

# download and unzip inspector-sbomgen
RUN wget https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/amd64/inspector-sbomgen.zip
RUN unzip inspector-sbomgen.zip

# find the inspector-sbomgen binary and move it to /
RUN find ./ -name inspector-sbomgen -type f -exec mv {} / \;
RUN chmod +x inspector-sbomgen

ENTRYPOINT ["/inspector-sbomgen"]

