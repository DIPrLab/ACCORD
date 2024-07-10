document.getElementById('showConstraints').addEventListener('click', async function() {
    const constraintsTable = document.getElementById('constraintsTable').getElementsByTagName('tbody')[0];
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.textContent = 'Fetching constraints...';
    constraintsTable.innerHTML = '';  // Clear the table

    try {
        const response = await fetch('/fetch_actionConstraints', { method: 'POST' });
        const constraints = await response.json();

        constraints.forEach((constraint, index) => {
            setTimeout(() => {
                const row = constraintsTable.insertRow();
                const cell1 = row.insertCell(0);
                const cell2 = row.insertCell(1);
                const cell3 = row.insertCell(2);
                const cell4 = row.insertCell(3);
                const cell5 = row.insertCell(4);
                const cell6 = row.insertCell(5);

                cell1.innerHTML = index + 1;
                cell2.innerHTML = constraint.TimeStamp;
                cell3.innerHTML = constraint.ConstraintTarget;
                cell4.innerHTML = constraint.Constraint;
                cell5.innerHTML = constraint.ConstraintOwner;
                cell6.innerHTML = constraint.File;
            }, 10 * index);
        });

        statusMessage.textContent = 'Action Constraints Fetched';
    } catch (error) {
        console.error('Error fetching constraints:', error);
        statusMessage.textContent = 'Failed to fetch constraints';
    }
});
