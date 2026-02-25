FROM registry.access.redhat.com/ubi9/python-312:9.7

ENV SUMMARY="Kubernetes aggregator MCP server" \
    DESCRIPTION="MCP server aggregating access to individual node-level MCP servers on a k8s cluster."

LABEL name="k8s-aggregator-mcp-server" \
      summary="${SUMMARY}" \
      description="${DESCRIPTION}" \
      io.k8s.display-name="k8s-aggregator-mcp-server" \
      io.k8s.description="${DESCRIPTION}" \
      io.openshift.tags="mcp,python"

# Install requirements
COPY --chown=1001:0 requirements.txt /opt/app/requirements.txt
WORKDIR /opt/app
RUN pip install --no-cache-dir -r requirements.txt

# Copy server
COPY --chown=1001:0 server.py /opt/app/server.py

EXPOSE 9029

WORKDIR /opt/app
ENTRYPOINT ["python", "server.py"]
