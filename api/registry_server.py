"""
api.registry_server

A2A Registry Server 

Functionalities:    
    - Load agent cards from a persisted registry.json file at startup
    - Validate agent cards for A2A compliance
    - Register, update, and delete agents at runtime
    - Persist registry changes back to registry.json
    - Expose dynamic discovery endpoints
"""
import json, logging, re, uvicorn

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

# Import agent validator
from scripts.validate_agent import AgentValidator

# === Configuration ===
BASE_DIR = Path(__file__).resolve().parent.parent # Resolve repository root
REGISTRY_PATH = BASE_DIR / "docs/registry.json" 

# === Pydantic Models ===
class Skill(BaseModel):
    """
    A single skill exposed by an agent.
    """
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory = list)

class AgentCardModel(BaseModel):
    """
    A2A Agent Card definition.
    """
    protocolVersion: str
    name: str
    description: str
    url: HttpUrl
    version: str

    author: Optional[str] = None
    wellKnownURI: Optional[HttpUrl] = None

    capabilities: Dict[str, bool] = Field(default_factory = dict)
    skills: List[Skill] = Field(default_factory = list)

    defaultInputModes: List[str] = Field(default_factory = list)
    defaultOutputModes: List[str] = Field(default_factory = list)

class ValidationResult(BaseModel):
    """ 
    Response model for validation-only endpoint.
    """
    valid: bool
    agentId: Optional[str] = None
    errors: List[str] = Field(default_factory = list)

# === Helper Functions ===
def compute_agent_id(card:AgentCardModel) -> str:
    """
    Compute a deterministic agent ID derived from agent name.
    """
    slug = card.name.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    return slug

def validate_agent_card(agent: AgentCardModel) -> List[str]:
    """
    Run A2A compliance validation using existing validator.
    """
    agent_dict = agent.model_dump()
    return validator.validate_a2a_compliance(agent_dict)

def load_registry() -> Dict[str, AgentCardModel]:
    """
    Load agents from registry.json into memory at startup.
    """
    if not REGISTRY_PATH.exists():
        return {}
    
    try:
        with open(REGISTRY_PATH, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse {REGISTRY_PATH}: {e}")
        return {}

    agents = {}
    for agent in data.get("agents", []):
        try:
            # Map backup format to AgentCardModel
            model = AgentCardModel(
                protocolVersion = agent.get("protocolVersion", "0.3.0"),
                name = agent.get("name", ""),
                description = agent.get("description", ""),
                url = agent.get("url", ""),
                version = agent.get("version", "1.0.0"),
                author = agent.get("author", ""),
                wellKnownURI = agent.get("wellKnownURI", ""),
                capabilities = agent.get("capabilities", {}),
                skills = agent.get("skills", []),
                defaultInputModes = agent.get("defaultInputModes", []),
                defaultOutputModes = agent.get("defaultOutputModes", [])
            )
        except Exception as e:
            logging.warning(f"Skipping invalid agent entry: {e}")
            continue
        agent_id = compute_agent_id(model)
        agents[agent_id] = model
    
    return agents

def save_registry(registry_path: Path, agents_dict: Dict[str, AgentCardModel]) -> None:
    """
    Save the registry.json in backup-compatible format.
    """
    agents_list = []

    for agent in agents_dict.values():
        agent_id = compute_agent_id(agent)
        agent_dict = agent.model_dump() # Convert AgentCardModel to plain dict

        # Convert skills to plain dicts 
        agent_dict["skills"] = [s.model_dump() if isinstance(s, Skill) else s for s in agent_dict.get("skills", [])]

        # Wrap in backup-compatible format
        agents_list.append({
            "_id": agent_id,
            "_registryMetadata": {"id": agent_id, "source": f"agents/{agent_id}.json"},
            "_source": f"agents/{agent_id}.json",
            "author": agent_dict.get("author", ""),
            "capabilities": agent_dict.get("capabilities", {}),
            "defaultInputModes": agent_dict.get("defaultInputModes", []),
            "defaultOutputModes": agent_dict.get("defaultOutputModes", []),
            "description": agent_dict.get("description", ""),
            "iconUrl": agent_dict.get("iconUrl", ""),
            "documentationUrl": agent_dict.get("documentationUrl", ""),
            "name": agent_dict.get("name", ""),
            "protocolVersion": agent_dict.get("protocolVersion", ""),
            "provider": agent_dict.get("provider", {}),
            "skills": agent_dict.get("skills", []),
            "url": str(agent_dict.get("url", "")), # Convert HttpUrl to str
            "version": agent_dict.get("version", ""),
            "wellKnownURI": str(agent_dict.get("wellKnownURI", "")), # Convert HttpUrl to str
        })

    tmp_path = registry_path.with_suffix(".tmp")
    try:
        registry_path.parent.mkdir(parents = True, exist_ok = True)
        with open(tmp_path, "w") as f:
            json.dump({"agents": agents_list}, f, indent = 2)
        tmp_path.replace(registry_path)
    except Exception as e:
        logging.error(f"Failed to save registry: {e}")
        if tmp_path.exists():
            tmp_path.unlink()

# === Registry State ===
AGENTS: Dict[str, AgentCardModel] = load_registry() # In-memory registry populated from disk at startup
validator = AgentValidator()

# == FastAPI App ===
app = FastAPI(title = "A2A Agent Registry API", description = "Live registry for A2A agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5173"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# === Registry Endpoints ===
@app.post("/agents/validate", response_model = ValidationResult)
async def validate_agent(agent: AgentCardModel):
    """
    Validate if an Agent is compliant with the A2A protocol without publishing it.
    """
    errors = validate_agent_card(agent)
    agent_id = compute_agent_id(agent)

    return ValidationResult(valid = not errors, agentId = agent_id, errors = errors)

@app.post("/agents/register", response_model = AgentCardModel, status_code = 201)
async def register_agent(agent: AgentCardModel):
    """
    Register (or update) an Agent. Requires A2A protocol compliant JSON.
    """
    errors = validate_agent_card(agent)

    if errors:
        raise HTTPException(status_code = 400, detail = {"message": "Agent failed A2A validation", "errors": errors})

    agent_id = compute_agent_id(agent)
    AGENTS[agent_id] = agent
    save_registry(REGISTRY_PATH, AGENTS)

    logging.info(f"Registered agent: {agent_id}")
    return agent

@app.get("/agents/list", response_model = List[AgentCardModel])
async def list_agents():
    """
    Lists all currently registered agents.
    """
    return list(AGENTS.values())

@app.get("/agents/search", response_model = List[AgentCardModel])
async def search_agents(
    q: Optional[str] = Query(None, description = "Search term to match in any agent field"),
    skills: Optional[List[str]] = Query(None, description = "Filter by skill tags"),
    skip: int = Query(0, ge = 0, description = "Number of agents to skip for pagination"),
    limit: int = Query(50, ge = 1, le = 100, description = "Maximum number of agents to return"),
):
    """
    Search Agents by any field in the Agent Card or Skills.
    - `q`matches against agent name, description, author, or skill names/tags.s
    - `skills` matches agents that have at least one skill tag containing any of the filter strings.
    - Supports pagination witth `skip`and `limit`.
    """
    results = []
    search_term = q.lower().strip() if q else None
    skills_filters = [s.lower().strip() for s in skills] if skills else []

    for agent in AGENTS.values():
        # Match search term across fields
        matched = True
        if search_term:
            matched = (
                search_term in agent.name.lower()
                or search_term in agent.description.lower()
                or (agent.author and search_term in agent.author.lower())
                or any(
                    search_term in skill.name.lower() or any(search_term in tag.lower() for tag in skill.tags)
                    for skill in agent.skills
                )
            )
        if not matched:
            continue

        # Match skills filters (substring match)
        if skills_filters:
            agent_skill_tags = [tag.lower() for skill in agent.skills for tag in skill.tags]
            skill_matched = any(
                any(filter_term in tag for tag in agent_skill_tags)
                for filter_term in skills_filters
            )
            if not skill_matched:
                continue

        results.append(agent)

    # Apply pagination
    paged_results = results[skip : skip + limit]

    return paged_results

@app.get("/agents/{agent_id}", response_model = AgentCardModel)
async def get_agent(agent_id: str):
    """
    Get a specific Agent by its ID
    (ID should be the name of the Agent in lowercase, with whitespaces being replaced with hyphens (e.g.: hello-world-agent)).
    """
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code = 404, detail = "Agent not found")
    return agent

@app.delete("/agents/{agent_id}", status_code = 204)
async def delete_agent(agent_id: str):
    """
    Remove Agent specified by ID from the Registry
    (ID should be the name of the Agent in lowercase, with whitespaces being replaced with hyphens (e.g.: hello-world-agent)).
    """
    if agent_id not in AGENTS:
        raise HTTPException(status_code = 404, detail = "Agent not found")
    
    AGENTS.pop(agent_id)
    save_registry(REGISTRY_PATH, AGENTS)

    logging.info(f"Deleted Agent: {agent_id}")
    return None

@app.get("/.well-known/agents/{agent_id}/card.json", response_model = AgentCardModel)
async def get_agent_card_well_known(agent_id: str):
    """
    Well-known endpoint for specified Agent Card discovery
    (ID should be the name of the Agent in lowercase, with whitespaces being replaced with hyphens (e.g.: hello-world-agent)).
    """
    agent = AGENTS.get(agent_id)

    if not agent:
        raise HTTPException(status_code = 404, detail = "Agent not found")
    
    return agent

@app.get("/registry")
async def get_registry():
    """
    Dynamic replacement for registry.json.
    """
    return {
        "version": "1.0.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(AGENTS),
        "agents": list(AGENTS.values()),
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}

# === Entrypoint ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)