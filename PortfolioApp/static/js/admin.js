function operateFormatter(value, row, index) {
    return [
        '<a class="edit ml10" href="javascript:void(0)" title="Edit" data-bs-toggle="modal" data-bs-target="#editModal">',
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


function populateModal(tableId, rowData) {
    const form = document.getElementById('editForm');
    form.innerHTML = ''; // Clear the form

    // Define the schema for each table to control which fields are displayed in the modal
    const tableSchemas = {
        submissionsTable: ['name', 'email', 'subject', 'message'],
        categoriesTable: ['category', 'subcategory']
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
            updatedData[key] = document.getElementById(key).value;
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
    var myModal = new bootstrap.Modal(document.getElementById('editModal'), {});
    myModal.show();
}


function handleAdd(tableId) {
    if (tableId === 'submissionsTable') {
        // Use prompts for simplicity. In a real scenario, you'd probably use a form or a modal.
        const newName = prompt('Enter name');
        const newEmail = prompt('Enter email');
        const newSubject = prompt('Enter subject');
        const newMessage = prompt('Enter message');

        if (newName && newEmail && newSubject && newMessage) {
            // Make AJAX call to create_submission endpoint with the new data
            $.post(`/create_submission`, {
                name: newName,
                email: newEmail,
                subject: newSubject,
                message: newMessage
            }, function (data) {
                if (data.status === 'success') {
                    $(`#${tableId}`).bootstrapTable('refresh');
                }
            });
        }
    } else if (tableId === 'categoriesTable') {
        // Get values from modal's input fields
        const newCategory = document.getElementById('categoryName').value;
        const newSubcategory = document.getElementById('subcategoryName').value;

        if (newCategory && newSubcategory) {
            $.post(`/create_category`, {
                category: newCategory,
                subcategory: newSubcategory
            }, function (data) {
                if (data.status === 'success') {
                    // Refresh the table
                    $(`#${tableId}`).bootstrapTable('refresh');

                    // Clear the input fields
                    document.getElementById('categoryName').value = '';
                    document.getElementById('subcategoryName').value = '';

                    // Close the modal
                    $('#add-cat-modal').modal('hide');
                }
            });
        }
    } 
}

function handleEdit(tableId, id, row) {
    if (tableId === 'submissionsTable') {
        // Assuming you want to use the same prompts for other tables, but you can differentiate them based on tableId
        const newName = row.name;
        const newEmail = row.email;
        const newSubject = row.subject;
        const newMessage = row.message;

        console.log(id,row);

        if (newName !== null && newEmail !== null && newSubject !== null && newMessage !== null) {
            // Make AJAX call to update_submission endpoint with the new data
            $.post(`/update_submission/${id}`, {
                name: newName,
                email: newEmail,
                subject: newSubject,
                message: newMessage
            })
            .done(function (data) {
                if (data.status === 'success') {
                    $(`#${tableId}`).bootstrapTable('refresh');
                }
            })
            .fail(function (xhr, status, error) {
                console.error("Submission Error:", error);
                alert("Failed to update the submission. Please try again.");
            });
        }
    } else if (tableId === 'categoriesTable') {
        // Assuming you want to use the same prompts for other tables, but you can differentiate them based on tableId
        const newCategory = row.category;
        const newSubcategory = row.subcategory;

        if (newCategory !== null && newSubcategory !== null) {
            // Make AJAX call to update_submission endpoint with the new data
            $.post(`/update_category/${id}`, {
                category: newCategory,
                subcategory: newSubcategory
            }, function (data) {
                if (data.status === 'success') {
                    $(`#${tableId}`).bootstrapTable('refresh');
                }
            });
        }
    }
}

function handleRemove(tableId, row) {
    if (tableId === 'submissionsTable') {
        // Make AJAX call to delete_submission endpoint
        $.post(`/delete_submission/${row.id}`, function (data) {
            if (data.status === 'success') {
                $(`#${tableId}`).bootstrapTable('remove', {
                    field: 'id',
                    values: [row.id]
                });
            }
        });
    } else if (tableId === 'categoriesTable') {
        // Make AJAX call to delete_submission endpoint
        $.post(`/delete_category/${row.id}`, function (data) {
            if (data.status === 'success') {
                $(`#${tableId}`).bootstrapTable('remove', {
                    field: 'id',
                    values: [row.id]
                });
            }
        });
    }
}

