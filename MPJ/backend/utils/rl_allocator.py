# backend/utils/rl_allocator.py
import os, math, random, json
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque, namedtuple

Device = "cuda" if torch.cuda.is_available() else "cpu"

# -----------------------------
# Feature engineering
# -----------------------------
def mk_state(incident, hospital, amb):
    """
    incident: {lat, lon}
    hospital: {lat, lon}
    amb: mongo doc for one ambulance
    Returns 1D feature vector (list of floats)
    """
    def hav_km(a,b,c,d):
        from math import radians, sin, cos, sqrt, atan2
        R=6371
        dlat=radians(c-a); dlon=radians(d-b)
        s=sin(dlat/2)**2+cos(radians(a))*cos(radians(c))*sin(dlon/2)**2
        return 2*R*atan2(sqrt(s), sqrt(1-s))
    dist_inc = hav_km(incident["lat"], incident["lon"], amb["latitude"], amb["longitude"])
    dist_hosp = hav_km(amb["latitude"], amb["longitude"], hospital["lat"], hospital["lon"])
    fuel = float(amb.get("fuel_level", 80))
    acc  = float(amb.get("location_accuracy", 25))
    status = amb.get("status","available")
    st = {
        "available":1, "dispatched":0.6, "en_route":0.4,
        "on_scene":0.5, "transporting":0.2, "at_hospital":0.7,
        "maintenance":0.1
    }.get(status,0.5)
    # Normalize roughly
    return [
        dist_inc/20.0,       # scaled
        dist_hosp/20.0,      # scaled
        fuel/100.0,
        min(acc,100.0)/100.0,
        st
    ]

# -----------------------------
# Tiny DQN
# -----------------------------
class QNet(nn.Module):
    def __init__(self, in_dim, hidden=64):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.q   = nn.Linear(hidden, 1)   # outputs Q-value for this (state, action)
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.q(x)

class DQNAllocator:
    """
    Inference-first: if weights not found -> use heuristic fallback (nearest).
    During allocate(), we compute Q for each available ambulance independently
    and pick argmax(Q). You can train offline with .train_on_batch()
    and save weights to disk.
    """
    def __init__(self, weights_path="allocator_q.pt"):
        self.in_dim = 5
        self.net = QNet(self.in_dim).to(Device)
        self.weights_path = weights_path
        self.loaded = False
        if os.path.exists(self.weights_path):
            try:
                self.net.load_state_dict(torch.load(self.weights_path, map_location=Device))
                self.net.eval()
                self.loaded = True
            except Exception:
                self.loaded = False

    def score(self, state_list):
        # state_list: list of state vectors
        with torch.no_grad():
            x = torch.tensor(state_list, dtype=torch.float32, device=Device)
            q = self.net(x).squeeze(-1)     # [N]
            return q.detach().cpu().numpy().tolist()

    def pick(self, incident, hospital, ambulances):
        """
        Returns index of chosen ambulance (in list) and scores
        Fallback to nearest if weights are unavailable.
        """
        # If no weights -> nearest available
        if not self.loaded:
            # Nearest based on incident distance
            def hav(a,b,c,d):
                from math import radians,sin,cos,sqrt,atan2
                R=6371; dlat=radians(c-a); dlon=radians(d-b)
                s=sin(dlat/2)**2+cos(radians(a))*cos(radians(c))*sin(dlon/2)**2
                return 2*R*atan2(sqrt(s), sqrt(1-s))
            dists = [hav(incident["lat"],incident["lon"], a["latitude"],a["longitude"]) for a in ambulances]
            idx = min(range(len(ambulances)), key=lambda i:dists[i])
            return idx, None

        states = [mk_state(incident,hospital,a) for a in ambulances]
        qs = self.score(states)
        idx = max(range(len(qs)), key=lambda i: qs[i])
        return idx, qs

# Optional minimal trainer (use synthetic logs) — not used by API path
def quick_train_synthetic(weights_out="allocator_q.pt", epochs=2000):
    net = QNet(5).to(Device)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    for step in range(epochs):
        # synthetic random states + shaped reward: higher reward for close-to-incident and higher fuel, lower for accuracy
        import random
        batch = torch.tensor([
            [random.random(), random.random(), random.random(), random.random(), random.random()]
            for _ in range(64)
        ], dtype=torch.float32, device=Device)
        # pretend reward (bigger is better): want low dist_inc (x0), high fuel (x2), low acc (x3), ok status (x4), small dist_hosp (x1)
        target =  1.2*(1.0 - batch[:,0]) \
                + 0.8*(1.0 - batch[:,1]) \
                + 0.7*batch[:,2] \
                + 0.3*batch[:,4] \
                - 0.4*batch[:,3]
        pred = net(batch).squeeze(-1)
        loss = F.mse_loss(pred, target.detach())
        opt.zero_grad(); loss.backward(); opt.step()
    torch.save(net.state_dict(), weights_out)
    return weights_out
