"""Model Context Protocol tools for a trusted local research session."""

from mcp.server.fastmcp import FastMCP


def server(lab):
    mcp = FastMCP(
        "Synthetic Lab",
        instructions=(
            "Discover laboratories and their instrument actions. Bare numbers use the documented units. "
            "Use operation_id for retrying the same action. Readouts come from persistent simulations. "
            "Model configuration and seeds belong to the researcher setting up the experiment."
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
    def operate(
        session: str,
        action: str,
        parameters: dict,
        operation_id: str,
        expected_revision: int | None = None,
    ) -> dict:
        """Operate an instrument, wait, or measure. Reuse the operation ID on retry."""
        return lab.act(
            session,
            action,
            parameters,
            operation_id=operation_id,
            expected_revision=expected_revision,
        )

    @mcp.tool()
    def fork(session: str, revision: int | None = None) -> dict:
        """Branch a simulation at a saved revision, preserving its state and noise sequence."""
        return lab.fork(session, at_revision=revision).status()

    @mcp.tool()
    def history(session: str, after: int = 0) -> list[dict]:
        """Read observable actions and measurements after a revision."""
        return lab.history(session, after=after)

    return mcp
