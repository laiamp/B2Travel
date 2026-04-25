import numpy as np
from umap import UMAP

def compute_projections(embeddings: list[list[float]], n_components: int = 3) -> list[tuple[float, float, float]]:
    if not embeddings:
        return []
        
    n_samples = len(embeddings)
    if n_samples < 2:
        return [(0.0,) * n_components] * n_samples
        
    n_neighbors = min(15, n_samples - 1)
    
    reducer = UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        metric="cosine",
        min_dist=0.5,
        random_state=42
    )
    embeddings_np = np.array(embeddings)
    
    projections = reducer.fit_transform(embeddings_np)
    
    return [tuple(float(v) for v in p) for p in projections]
