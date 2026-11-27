"""Model Context Protocol tools for a trusted research session."""

from mcp.server.fastmcp import FastMCP


def server(lab):
    mcp = FastMCP(
        "Synthetic Lab",
        instructions=(
            "Discover laboratories and their instrument actions. Bare numbers use the documented "
            "units. Use operation_id for retrying the same action. Long calculations may be "
            "submitted and read later. Model configuration and seeds belong to the researcher "
            "setting up the experiment."
        ),
    )

    @mcp.tool()
    def laboratories() -> list[dict]:
        """List models and each action's parameters, bounds and physical units."""
        return lab.catalogue()

    @mcp.tool()
    def sessions() -> list[dict]:
        """List experiment sessions stored in this server's database."""
        return lab.list_sessions()

    @mcp.tool()
    def create(model: str) -> dict:
        """Start an independent synthetic specimen with fresh latent parameters."""
        return lab.create(model).status()

    @mcp.tool()
    def observe_configuration(session: str) -> dict:
        """Read instrument settings and revision. Use read to acquire a measurement."""
        return lab.status(session)

    @mcp.tool()
    def experiment_description(session: str) -> dict:
        """Read a persisted laboratory description without installing its solver."""
        return lab.describe_session(session)

    @mcp.tool()
    def operate(
        session: str,
        action: str,
        parameters: dict,
        operation_id: str,
        expected_revision: int | None = None,
    ) -> dict:
        """Operate an instrument and wait for the result."""
        return lab.act(
            session,
            action,
            parameters,
            operation_id=operation_id,
            expected_revision=expected_revision,
        )

    @mcp.tool()
    def submit_operation(
        session: str,
        action: str,
        parameters: dict,
        operation_id: str,
        expected_revision: int | None = None,
    ) -> dict:
        """Queue a long operation without waiting for numerical work to finish."""
        return lab.submit(
            session,
            action,
            parameters,
            operation_id=operation_id,
            expected_revision=expected_revision,
        )

    @mcp.tool()
    def operation_status(session: str, operation_id: str) -> dict:
        """Read the state and result of a submitted operation."""
        return lab.operation(session, operation_id)

    @mcp.tool()
    def artifact_information(artifact_id: str) -> dict:
        """Describe an external image, spectrum, field or trajectory by artifact ID."""
        return lab.artifact_info(artifact_id)

    @mcp.tool()
    def artifact_chunk(artifact_id: str, offset: int = 0, limit: int = 65536) -> dict:
        """Read up to one MiB as base64; use next_offset to continue until eof."""
        return lab.read_artifact_chunk(artifact_id, offset=offset, limit=limit)

    @mcp.tool()
    def fork(session: str, revision: int | None = None) -> dict:
        """Branch a simulation at a saved revision, preserving its state and noise sequence."""
        return lab.fork(session, at_revision=revision).status()

    @mcp.tool()
    def history(session: str, after: int = 0) -> list[dict]:
        """Read observable actions and measurements after a revision."""
        return lab.history(session, after=after)

    return mcp
