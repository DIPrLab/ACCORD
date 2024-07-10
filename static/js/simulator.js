document.addEventListener("DOMContentLoaded", function() {
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('click', function() {
            const conflictAction = this.querySelector('.conflict-action').textContent.trim();
            const numUsers = document.getElementById('num-users').value;
            const numActions = document.getElementById('num-actions').value;

            // Display simulation status
            const simulatorDiv = document.getElementById('simulator');
            simulatorDiv.innerHTML = '<p>Simulation in progress...</p>';
            simulatorDiv.style.display = 'block';

            // Using fetch to send data to the server
            fetch('/simulate_actions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conflictAction: conflictAction,
                    numUsers: numUsers,
                    numActions: numActions
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Hide the current cards
                    document.getElementById('demo-tasks').style.display = 'none';

                    // Prepare table to display the action logs
                    const table = document.createElement('table');
                    table.setAttribute('class', 'table table-striped');
                    table.style.width = '100%';
                    const thead = document.createElement('thead');
                    const tbody = document.createElement('tbody');
                    table.appendChild(thead);
                    table.appendChild(tbody);

                    // Create header row
                    const headerRow = document.createElement('tr');
                    const headers = ['S.No', 'Actor Performing', 'Action Performed', 'Target Actor', 'Filename', 'Constraint'];
                    headers.forEach(text => {
                        const headerCell = document.createElement('th');
                        headerCell.textContent = text;
                        headerCell.style.textAlign = 'center';
                        headerRow.appendChild(headerCell);
                    });
                    thead.appendChild(headerRow);

                    // Append table to the simulator division
                    simulatorDiv.appendChild(table);

                    // Add rows with delay
                    data.actions.forEach((action, index) => {
                        setTimeout(() => {
                            const row = document.createElement('tr');
                            const rowData = [
                                index + 1,
                                action.performingUser.split('@')[0], // Remove domain part
                                action.action,
                                action.targetUser.split('@')[0], // Remove domain part
                                action.fileName,
                                ''
                            ];
                            rowData.forEach((text, idx) => {
                                const cell = document.createElement('td');
                                cell.textContent = text;
                                cell.style.textAlign = 'center';
                                if (idx === 5) { // Constraint column with checkbox
                                    const checkbox = document.createElement('input');
                                    checkbox.type = 'checkbox';
                                    checkbox.setAttribute('data-action', JSON.stringify(action));
                                    checkbox.onchange = checkboxChange;
                                    cell.textContent = '';
                                    cell.appendChild(checkbox);
                                }
                                row.appendChild(cell);
                            });
                            tbody.appendChild(row);

                            // Update status when completed
                            if (index === data.actions.length - 1) {
                                simulatorDiv.querySelector('p').textContent = 'Simulation completed.';
                                addGenerateConstraintButton(simulatorDiv, table);
                            }
                        }, 100 * index);
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                simulatorDiv.innerHTML = '<p>Error during simulation.</p>';
            });
        });
    });
});

function checkboxChange() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    const button = document.getElementById('generate-constraint-button');
    button.disabled = !Array.from(checkboxes).some(checkbox => checkbox.checked);
}

function addGenerateConstraintButton(parentDiv, table) {
    const button = document.createElement('button');
    button.textContent = 'Generate Constraint';
    button.id = 'generate-constraint-button';
    button.disabled = true;
    button.style.margin = '20px auto';
    button.style.display = 'block';
    button.onclick = () => {
        const selectedActions = [];
        document.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
            selectedActions.push(JSON.parse(checkbox.getAttribute('data-action')));
        });
        // Send the selected actions to the server
        fetch('/addActionConstraints', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({actions: selectedActions})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Constraints successfully added!');
            } else {
                alert('Failed to add constraints.');
            }
        })
        .catch(error => console.error('Error:', error));
    };
    parentDiv.appendChild(button);
}
