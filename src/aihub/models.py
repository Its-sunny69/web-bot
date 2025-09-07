from django.db import models
from pgvector.django import VectorField
from preview.models import RepositoryFile,Repository


class CodeEmbedding(models.Model):
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    file = models.ForeignKey(RepositoryFile, on_delete=models.CASCADE)
    file_path = models.TextField()           
    chunk_id = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()             
    embedding = VectorField(dimensions=384) 
    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["repo_id"]),
            models.Index(fields=["file_path"]),
        ]
        unique_together = ("repo_id", "file_path", "chunk_id")

    def __str__(self):
        return f"{self.repo_id}::{self.file_path}::{self.chunk_id or 'full'}"
