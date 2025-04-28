from rdflib import Graph, RDF, RDFS, OWL, URIRef
from rdflib.collection import Collection
from collections import defaultdict, deque

# --- Load Graph ---
def load_graph(ttl_path):
    g = Graph()
    g.parse(ttl_path, format='turtle')
    return g

# --- Extract Schema and KB Elements ---
def extract_elements(g):
    # Classes and Instances
    classes = set(g.subjects(RDF.type, OWL.Class)) \
              | set(g.subjects(RDF.type, RDFS.Class))
    all_typed = set(g.subjects(RDF.type, None))
    instances = all_typed - classes

    # Subclass axioms 
    subclass_triples = [
        (s, o) for s, o in g.subject_objects(RDFS.subClassOf)
        if s in classes and o in classes
    ]
    num_subclasses = len(subclass_triples)

    # Expand owl:AllDisjointClasses into direct owl:disjointWith triples

    extra_disjoints = set()
    for bn in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members_node = next(g.objects(bn, OWL.members), None)
        if members_node:
            col = Collection(g, members_node)
            items = list(col)
            for a in items:
                for b in items:
                    if a != b and a in classes and b in classes:
                        extra_disjoints.add((a, OWL.disjointWith, b))

    # Non-inheritance class-to-class relationships
    noninherit_rels = set(
        (s, p, o)
        for s, p, o in g.triples((None, None, None))
        if s in classes
        and isinstance(o, URIRef) and o in classes
        and p != RDFS.subClassOf
    )
    noninherit_rels |= extra_disjoints
    num_noninherit = len(noninherit_rels)

    # Object and Data Properties
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))

    # Map of instances per class
    class_instances = defaultdict(int)
    for inst in instances:
        for cls in g.objects(inst, RDF.type):
            if cls in classes:
                class_instances[cls] += 1

    return {
        'classes': classes,
        'instances': instances,
        'obj_props': obj_props,
        'data_props': data_props,
        'num_subclasses': num_subclasses,
        'num_noninherit': num_noninherit,
        'class_instances': class_instances
    }

# --- Schema Metrics ---
def relationship_richness(num_noninherit, num_subclasses):
    total = num_noninherit + num_subclasses
    return (num_noninherit / total) if total > 0 else 0

def inheritance_richness(num_subclasses, num_classes):
    return num_subclasses / num_classes if num_classes > 0 else 0

def attribute_richness(num_data_props, num_classes):
    return num_data_props / num_classes if num_classes > 0 else 0

# --- Knowledge Base Metrics ---
def class_richness(num_classes, class_instances):
    non_empty = len([c for c, count in class_instances.items() if count > 0])
    return non_empty / num_classes if num_classes > 0 else 0


def class_connectivity(g, classes):
    connectivity = {}
    for cls in classes:
        total_links = 0
        for inst in g.subjects(RDF.type, cls):
            for p, o in g.predicate_objects(inst):
                if isinstance(o, URIRef) and (o, RDF.type, None) in g:
                    total_links += 1
        connectivity[cls] = total_links
    return connectivity


def class_importance(g, classes, class_instances):
    # Build subclass map
    subclass_map = defaultdict(list)
    for s, o in g.subject_objects(RDFS.subClassOf):
        if s in classes and o in classes:
            subclass_map[o].append(s)
    total_instances = sum(class_instances.values())
    importance = {}
    for cls in classes:
        # Gather all subclasses (including self)
        queue = deque([cls])
        subtree = set()
        while queue:
            c = queue.popleft()
            if c not in subtree:
                subtree.add(c)
                queue.extend(subclass_map.get(c, []))
        inst_count = sum(class_instances.get(c, 0) for c in subtree)
        importance[cls] = (inst_count / total_instances) if total_instances > 0 else 0
    return importance


def cohesion(g, instances, obj_props):
    # Build undirected adjacency among instances via object properties
    adj = defaultdict(set)
    for s, p, o in g.triples((None, None, None)):
        if p in obj_props and s in instances and isinstance(o, URIRef) and o in instances:
            adj[s].add(o)
            adj[o].add(s)
    visited = set()
    components = 0
    for inst in instances:
        if inst not in visited:
            components += 1
            # BFS
            queue = [inst]
            visited.add(inst)
            while queue:
                curr = queue.pop()
                for nbr in adj[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)
    return components


def per_class_relationship_richness(g, classes, obj_props):
    # Schema-level prop count per class (domain declarations)
    schema_props = defaultdict(set)
    for p in obj_props:
        for d in g.objects(p, RDFS.domain):
            if d in classes:
                schema_props[d].add(p)
    # Instance-level prop usage per class
    inst_usage = defaultdict(set)
    for cls in classes:
        for inst in g.subjects(RDF.type, cls):
            for p, o in g.predicate_objects(inst):
                if p in obj_props:
                    inst_usage[cls].add(p)
    # Compute ratio
    per_rr = {}
    for cls in classes:
        defined = schema_props.get(cls, set())
        used = inst_usage.get(cls, set())
        per_rr[cls] = (len(used) / len(defined)) if defined else 0
    return per_rr

# --- Main Script ---
if __name__ == '__main__':
    ttl_file = 'msws.ttl'
    g = load_graph(ttl_file)
    elems = extract_elements(g)

    C = len(elems['classes'])
    SC = elems['num_subclasses']
    NI = elems['num_noninherit']
    DP = len(elems['data_props'])

    # Schema Metrics
    RR = relationship_richness(NI, SC)
    IR = inheritance_richness(SC, C)
    AR = attribute_richness(DP, C)

    # KB Metrics
    CR = class_richness(C, elems['class_instances'])
    conn = class_connectivity(g, elems['classes'])
    imp = class_importance(g, elems['classes'], elems['class_instances'])
    coh = cohesion(g, elems['instances'], elems['obj_props'])
    per_rr = per_class_relationship_richness(g, elems['classes'], elems['obj_props'])

    # Output
    print(f"Classes: {C}")
    print(f"Subclass axioms: {SC}")
    print(f"Non-inheritance relations: {NI}")
    print(f"Data properties: {DP}")
    print(f"Instances: {len(elems['instances'])}\n")

    print("--- Schema Metrics ---")
    print(f"Relationship Richness (RR): {RR:.3f}")
    print(f"Inheritance Richness (IR): {IR:.3f}")
    print(f"Attribute Richness (AR): {AR:.3f}\n")

    print("--- Knowledge Base Metrics ---")
    print(f"Class Richness (CR): {CR:.3f}")
    print(f"Cohesion (connected components): {coh}\n")

    print("--- Class Connectivity (top 5) ---")
    for cls, links in sorted(conn.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{cls}: {links}")

    print("\n--- Class Importance (top 5) ---")
    for cls, val in sorted(imp.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{cls}: {val:.3f}")

    print("\n--- Per-Class Relationship Richness (top 5) ---")
    for cls, val in sorted(per_rr.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{cls}: {val:.3f}")
