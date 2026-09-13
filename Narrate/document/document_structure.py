from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Objective:
    objective: str
    sub_points: List[str]

@dataclass
class Resource:
    name: str
    description: str

@dataclass
class Phase:
    phase: str
    objectives: List[Objective] = field(default_factory=list)
    resources: Dict[str, List[Resource]] = field(default_factory=dict)

@dataclass
class PlanContent:
    mission_overview: str
    phases: List[Phase] = field(default_factory=list)
