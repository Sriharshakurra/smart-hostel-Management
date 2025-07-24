document.addEventListener('DOMContentLoaded', function () {
    const roomField = document.getElementById('id_room');
    const rentField = document.getElementById('id_total_rent');

    if (roomField && rentField) {
        roomField.addEventListener('change', function () {
            const roomId = roomField.value;

            if (!roomId) {
                rentField.value = '';
                return;
            }

            fetch(`/get-room-rent/${roomId}/`)
                .then(response => response.json())
                .then(data => {
                    rentField.value = data.rent || 0;
                })
                .catch(error => {
                    console.error('Error fetching rent:', error);
                    rentField.value = 0;
                });
        });
    }
});