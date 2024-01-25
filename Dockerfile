# we use alpine and not distroless because we need wget, unzip, etc.
FROM alpine:latest

# download and unzip inspector-sbomgen
#RUN wget https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/amd64/inspector-sbomgen.zip
#RUN unzip inspector-sbomgen.zip

# find the inspector-sbomgen binary and move it to the working directory
#RUN find ./ -name inspector-sbomgen -type f -exec mv {} /usr/local/bin/ \;

COPY inspector-sbomgen /usr/local/bin/

# entrypoint.sh invokes insptector-sbomgen with the correct CLI arguments
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
