from rdflib import Graph, RDF, RDFS, OWL
from collections import defaultdict

g = Graph()
g.parse("csws.ttl", format="ttl") 

classes = set(g.subjects(RDF.type, OWL.Class))
instances = set(g.subjects(RDF.type, None)) - classes  # Individuals, not classes

subclasses = set(g.triples((None, RDFS.subClassOf, None)))
num_subclasses = len(subclasses)

object_properties = set(g.subjects(RDF.type, OWL.ObjectProperty))
num_object_properties = len(object_properties)

data_properties = set(g.subjects(RDF.type, OWL.DatatypeProperty))
num_data_properties = len(data_properties)

# Classes with at least one instance
class_instances = defaultdict(int)
for s in instances:
    for o in g.objects(s, RDF.type):
        if o in classes:
            class_instances[o] += 1

# --------------------------------------------------
# 1. Schema Metrics
# --------------------------------------------------

# Relationship Richness (RR)
RR = num_object_properties / (num_object_properties + num_subclasses)

# Inheritance Richness (IR)
IR = num_subclasses / len(classes) 

# Attribute Richness (AR)
AR = num_data_properties / len(classes)

# --------------------------------------------------
# 2. Knowledge Base Metrics
# --------------------------------------------------

# Class Richness (CR)
CR = len(class_instances) / len(classes) if len(classes) > 0 else 0

# Class Connectivity (Conn)
# Count non-inheritance instance-to-instance links
def class_connectivity(ci):
    count = 0
    for s in g.subjects(RDF.type, ci):
        for p, o in g.predicate_objects(subject=s):
            if (o, RDF.type, None) in g: 
                count += 1
    return count


print("\n--- Schema Metrics ---")
print(f"Relationship Richness (RR): {RR:.3f}")
print(f"Inheritance Richness (IR): {IR:.3f}")
print(f"Attribute Richness (AR): {AR:.3f}")

print("\n--- Knowledgebase Metrics ---")
print(f"Class Richness (CR): {CR:.3f}")