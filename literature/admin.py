from django.contrib import admin
from .models import Post, Comment, Book, Author, Genre

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'book', 'status', 'publish')
    list_filter = ('status', 'publish', 'author')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author', 'book')
    date_hierarchy = 'publish'
    ordering = ('status', 'publish')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created', 'active')
    list_filter = ('active', 'created')
    search_fields = ('author__username', 'body')
    actions = ['approve_comments']

    def approve_comments(self, request, queryset):
        queryset.update(active=True)
    approve_comments.short_description = "Одобрить выбранные комментарии"

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'genre', 'published_date')
    list_filter = ('genre', 'published_date')
    search_fields = ('title', 'description')
    raw_id_fields = ('author', 'genre')

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('user', 'birth_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')