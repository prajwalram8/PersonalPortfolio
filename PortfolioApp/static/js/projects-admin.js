function operateFormatter(value, row, index) {
    return [
        '<a class="edit ml10" href="javascript:void(0)" title="Edit" data-bs-toggle="modal" data-bs-target="#edit-md-modal">',
        '<i class="bi bi-pencil-square"></i>',
        '</a>',
        '<a class="remove ml10" href="javascript:void(0)" title="Remove">',
        '<i class="bi bi-trash"></i>',
        '</a>'
    ].join('');
}

window.operateEvents = {
    'click .edit': function (e, value, row, index) {
        // Navigate to the th element and retrieve the data-table-id attribute
        const tableId = this.columns[0].tableId; 
        populateModal(tableId, row);
    },
    'click .remove': function (e, value, row, index) {
        // Navigate to the th element and retrieve the data-table-id attribute
        if (confirm("Are you sure you want to delete this row?")) {
        const tableId = this.columns[0].tableId; 
        handleRemove(tableId, row);
    }
    }
};

function populateCategoryDropdown(dropdownId) {
    $.get('/get_form_categories', function(data) {
        const dropdown = document.getElementById(dropdownId);
        dropdown.innerHTML = ""; // Clear existing options

        data.categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = `${cat.category} - ${cat.subcategory}`;
            dropdown.appendChild(option);
        });
    });
}

$('#add-md-modal').on('show.bs.modal', function() {
    populateCategoryDropdown('categoryDropdown');
});

$('#edit-md-modal').on('show.bs.modal', function() {
    populateCategoryDropdown('category_id');
});

function handleAdd(tableId) {
    if (tableId === 'markdownFilesTable') {
        const mdName = document.getElementById('mdName').value;
        const categoryId = document.getElementById('categoryDropdown').value;
        const authorName = document.getElementById('authorName').value;
        const mdFileInput = document.getElementById('mdFile');
        
        if (mdName && categoryId && authorName && mdFileInput.files[0]) {
            const file = mdFileInput.files[0];
            const reader = new FileReader();

            reader.onload = function(e) {
                const fileContent = e.target.result;
                
                $.post(`/create_markdown_file`, {
                    name: mdName,
                    category_id: categoryId,
                    content: fileContent,
                    author_name: authorName
                }, function (data) {
                    if (data.status === 'success') {
                        // Refresh the table
                        $(`#${tableId}`).bootstrapTable('refresh');

                        // Clear the input fields and close the modal
                        document.getElementById('addMdForm').reset();
                        $('#add-md-modal').modal('hide');
                    }
                });
            };
            
            reader.readAsText(file);
        }
    }
}

function handleEdit(tableId, id, row) {
    if (tableId === 'markdownFilesTable') {
        // Assuming you want to use the same prompts for other tables, but you can differentiate them based on tableId
        const mdName = row.name;
        const categoryId = row.category_id;
        const authorName = row.author_name;
        const mdFileInput = row.content;

        if (mdName && categoryId && authorName && mdFileInput.files[0]) {
            const file = mdFileInput.files[0];
            const reader = new FileReader();

            reader.onload = function(e) {
                const fileContent = e.target.result;
                
                $.post(`/update_markdown_file/${id}`, {
                    name: mdName,
                    category_id: categoryId,
                    content: fileContent,
                    author_name: authorName
                }, function (data) {
                    if (data.status === 'success') {
                        // Refresh the table
                        $(`#${tableId}`).bootstrapTable('refresh');

                        // Clear the input fields and close the modal
                        document.getElementById('editMdForm').reset();
                        $('#edit-md-modal').modal('hide');
                    }
                });
            };
            
            reader.readAsText(file);
        }
    }
}

function handleRemove(tableId, row) {
    if (tableId === 'markdownFilesTable') {
        // Make AJAX call to delete_submission endpoint
        $.post(`/delete_markdown_file/${row.id}`, function (data) {
            if (data.status === 'success') {
                $(`#${tableId}`).bootstrapTable('remove', {
                    field: 'id',
                    values: [row.id]
                });
            }
        });
    }
}

function populateModal(tableId, rowData) {
    const form = document.getElementById('editMdForm');
    form.innerHTML = ''; // Clear the form

    // Define the schema for each table to control which fields are displayed in the modal
    const tableSchemas = {
        markdownFilesTable: ['name', 'category_id', 'content', 'author_name']
        // Add additional tables as needed
    };

    const schema = tableSchemas[tableId];

    // Check if schema exists for the provided tableId
    if (!schema) {
        console.error(`No schema found for tableId: ${tableId}`);
        return;
    }

    // Dynamically create input fields based on the schema
    schema.forEach(key => {
        const value = rowData[key];
        if (key === 'category_id') {
            // Create label
            const label = document.createElement('label');
            label.setAttribute('for', key);
            label.className = 'form-label'
            label.innerText = key.charAt(0).toUpperCase() + key.slice(1);

            // Create input
            const input = document.createElement('select');
            input.setAttribute('id', key);
            input.className = 'form-control'
            input.value = value;

            // Append label and input to the form
            form.appendChild(label);
            form.appendChild(input);
            form.appendChild(document.createElement('br')); // Line break for better readability

        } else if (key === 'content') {
            // Create label
            const label = document.createElement('label');
            label.setAttribute('for', key);
            label.className = 'form-label'
            label.innerText = key.charAt(0).toUpperCase() + key.slice(1);

            // Create input
            const input = document.createElement('input');
            input.setAttribute('type', 'file');
            input.setAttribute('accept', '.md');
            input.setAttribute('id', key);
            input.className = 'form-control'

            // Append label and input to the form
            form.appendChild(label);
            form.appendChild(input);
            form.appendChild(document.createElement('br')); // Line break for better readability

        } else {
            // Create label
            const label = document.createElement('label');
            label.setAttribute('for', key);
            label.className = 'form-label'
            label.innerText = key.charAt(0).toUpperCase() + key.slice(1);

            // Create input
            const input = document.createElement('input');
            input.setAttribute('type', 'text');
            input.setAttribute('name', key);
            input.setAttribute('id', key);
            input.className = 'form-control'
            input.value = value;

            // Append label and input to the form
            form.appendChild(label);
            form.appendChild(input);
            form.appendChild(document.createElement('br')); // Line break for better readability
        }
                
        // Add a hidden input field for the id
        const idInput = document.createElement('input');
        idInput.setAttribute('type', 'hidden');
        idInput.setAttribute('name', 'id');
        idInput.setAttribute('id', 'id');
        idInput.value = rowData.id; // assuming rowData contains an id property
        form.appendChild(idInput);
    });

    // Add the submit button
    const submitButton = document.createElement('button');
    submitButton.setAttribute('type', 'submit');
    submitButton.className = 'btn btn-primary';
    submitButton.innerText = 'Update';
    form.appendChild(submitButton);

    submitButton.addEventListener('click', function(event) {
        // Prevent the default form submission
        event.preventDefault();
        
        // Create an object to store the new data
        const updatedData = {};

        // Iterate over schema to capture the updated form data
        schema.forEach(key => {
            if (key === 'content') {
                updatedData[key] = document.getElementById(key);
            } else {
                updatedData[key] = document.getElementById(key).value;
            }
        });

        // Retrieve the id from the form
        const id = document.getElementById('id').value;

        // Handle your logic here
        handleEdit(tableId, id, updatedData);

        // Forcefully remove the modal-backdrop if it doesn't get removed automatically
        const backdrop = document.querySelector(".modal-backdrop");
        if(backdrop) backdrop.remove();
    });

    // Show the modal
    var myModal = new bootstrap.Modal(document.getElementById('edit-md-modal'), {});
    myModal.show();
}


