const body = document.querySelector('body'),
    sidebar = body.querySelector('nav'),
    toggle = body.querySelector(".toggle"),
    searchBtn = body.querySelector(".search-box"),
    modeSwitch = body.querySelector(".toggle-switch"),
    modeText = body.querySelector(".mode-text"),
    prevBtn = document.getElementById('prevBtn'),
    nextBtn = document.getElementById('nextBtn');

toggle.addEventListener("click", () => {
    sidebar.classList.toggle("close");
})

searchBtn.addEventListener("click", () => {
    sidebar.classList.remove("close");
})

modeSwitch.addEventListener("click", () => {
    body.classList.toggle("dark");

    if (body.classList.contains("dark")) {
        modeText.innerText = "Light mode";
    } else {
        modeText.innerText = "Dark mode";

    }
});

prevBtn.addEventListener('click', function () {
    const container = document.querySelector('.gallery-container');
    container.scrollLeft -= 300; // Slide left by 300px, adjust as needed.
});

nextBtn.addEventListener('click', function () {
    const container = document.querySelector('.gallery-container');
    container.scrollLeft += 300; // Slide right by 300px, adjust as needed.
});