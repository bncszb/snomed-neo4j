# %%
#
from snomed_neo4j_core.models import Concept

Concept
# %%
c = Concept(id="131232", effectiveTime="20211212", active="1", moduleId="1212121212", definitionStatusId="2323233232")
c

# %%
print(c.model_dump_json())
# %%
