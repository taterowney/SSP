document.addEventListener('DOMContentLoaded', function() {

    function showModal(id) {
        document.getElementById(id).style.display = 'block';
    }

    for (elem of document.getElementsByClassName('close')) {
        elem.addEventListener('click', function() {
            let modal = this.parentElement.parentElement;
            modal.style.animation = 'fadeOut 0.5s forwards';
            modal.children[0].style.animation = 'scaleOut 0.5s forwards';
            setTimeout(function() {
                modal.style.display = 'none';
                modal.style.animation = 'fadeIn 0.5s';
                modal.children[0].style.animation = 'scaleIn 0.5s';
            }, 500);
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.animation = 'fadeOut 0.5s forwards';
           event.target.children[0].style.animation = 'scaleOut 0.5s forwards';
            setTimeout(function() {
                event.target.style.display = 'none';
                event.target.style.animation = 'fadeIn 0.5s';
                event.target.children[0].style.animation = 'scaleIn 0.5s';
            }, 500);
        }
    });

    document.showModal = showModal;

});
