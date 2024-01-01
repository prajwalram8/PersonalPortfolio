## HTML Templates
* ```admin.html:``` The main admin dashboard that shows a list of contact submissions, categories, and Markdown files. It should also provide links/buttons to create, edit, or delete categories and Markdown files.

* ```new_category.html```: A form to create a new category.

* ```edit_category.html```: A form to edit an existing category.

* ```new_markdown.html```: A form to create a new Markdown file.

* ```edit_markdown.html```: A form to edit an existing Markdown file.

## Views (views.py)
```/admin:``` This template will serve as the main dashboard for the admin panel. It will show a list of contact submissions, categories, and Markdown files. Additionally, it will provide options for creating, editing, or deleting categories and Markdown files.<br>
>GET: Load and display all contact submissions, categories, and Markdown files.

```/admin/create_category:``` To create a new category.
>POST: Logic to create a new category.

```/admin/edit_category/<int:category_id>:``` To edit an existing category.
>GET: Display the edit form pre-filled with the existing category info.<br>
>POST: Logic to update the category.

```/admin/delete_category/<int:category_id>:``` To delete a category.
>POST: Logic to delete the category.

```/admin/new_markdown:``` To create a new Markdown file.
>GET: Display the form to create a new Markdown file.<br>
>POST: Logic to create a new Markdown file.

```/admin/edit_markdown/<int:markdown_id>:``` To edit an existing Markdown file.
>GET: Display the edit form pre-filled with existing Markdown file info.<br>
>POST: Logic to update the Markdown file.

```/admin/delete_markdown/<int:markdown_id>:``` To delete a Markdown file.
>POST: Logic to delete the Markdown file.

## Models (models.py)
```ContactSubmission:``` To store contact submissions from the contact form.
>Fields: id, name, email, subject, message

```Category:``` To categorize Markdown files.
>Fields: id, name

```Relationships:``` One-to-many with MarkdownFile
>MarkdownFile: To store Markdown files.

Fields: id, filename, title, category_id
Relationships: Many-to-one with Category