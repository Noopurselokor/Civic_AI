"""Two-stage duplicate detection: geo-filter, then CLIP embedding similarity."""

def find_duplicate(lat, lng, category, image_embedding):
    # TODO: Stage 1 - PostGIS ST_DWithin query for nearby same-category reports
    # TODO: Stage 2 - cosine similarity on CLIP embeddings for candidates
    pass
