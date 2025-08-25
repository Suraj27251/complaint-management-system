document.addEventListener('DOMContentLoaded', function () {
    const menuButton = document.getElementById('menuButton');
    const nav = document.getElementById('mainNav');
    const overlay = document.getElementById('sidebarOverlay');
    if (menuButton && nav && overlay) {
        menuButton.addEventListener('click', function () {
            nav.classList.toggle('open');
            overlay.classList.toggle('show');
        });
        overlay.addEventListener('click', function () {
            nav.classList.remove('open');
            overlay.classList.remove('show');
        });
    }
});
