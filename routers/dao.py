
# routers/dao.py

from fastapi import APIRouter, Request, HTTPException
import logging
from web3 import Web3
import json
import os

router = APIRouter(prefix="/dao", tags=["governance"])

# Config Web3
INFURA_KEY = os.getenv("INFURA_KEY")
CONTRACT_ADDRESS = os.getenv("DAO_CONTRACT_ADDRESS")
ABI_PATH = os.getenv("DAO_ABI_PATH", "ZIMADaoABI.json")

w3 = Web3(Web3.HTTPProvider(f"https://rpc-sepolia.infura.io/v3/{INFURA_KEY}"))

with open(ABI_PATH) as f:
    abi = json.load(f)

dao = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)

# === Endpoint: Ejecutar propuesta DAO ===
@router.post("/execute")
async def execute_proposal(request: Request):
    payload = await request.json()
    desc = payload.get("description", "")
    logging.info(f"[DAO] Ejecutando acción: {desc}")
    # Acá podrías mapear strings de descripción a acciones reales
    return {"status": "executed", "description": desc}

# === Endpoint: Listar propuestas ===
@router.get("/proposals")
async def list_proposals():
    count = dao.functions.getProposalCount().call()
    proposals = []
    for i in range(count):
        desc, yes, no, deadline, executed = dao.functions.proposals(i).call()
        proposals.append({
            "id": i,
            "description": desc,
            "yes_votes": yes,
            "no_votes": no,
            "deadline": deadline,
            "executed": executed
        })
    return {"proposals": proposals}
