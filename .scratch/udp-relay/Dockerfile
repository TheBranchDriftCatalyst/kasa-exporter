FROM alpine:latest

RUN apk add --no-cache socat

# Kasa devices use UDP port 9999 and 20002
EXPOSE 9999/udp 20002/udp

# Script to relay UDP broadcasts
COPY relay.sh /relay.sh
RUN chmod +x /relay.sh

CMD ["/relay.sh"]
