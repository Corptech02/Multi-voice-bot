const ROWS = 6;
const COLS = 7;
const EMPTY = 0;
const PLAYER1 = 1;
const PLAYER2 = 2;

let board = [];
let currentPlayer = PLAYER1;
let gameOver = false;

function initializeBoard() {
    board = [];
    for (let r = 0; r < ROWS; r++) {
        board[r] = [];
        for (let c = 0; c < COLS; c++) {
            board[r][c] = EMPTY;
        }
    }
}

function createBoardElement() {
    const boardElement = document.getElementById('board');
    boardElement.innerHTML = '';
    
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.row = r;
            cell.dataset.col = c;
            cell.addEventListener('click', handleCellClick);
            boardElement.appendChild(cell);
        }
    }
}

function handleCellClick(event) {
    if (gameOver) return;
    
    const col = parseInt(event.target.dataset.col);
    const row = getAvailableRow(col);
    
    if (row === -1) return; // Column is full
    
    board[row][col] = currentPlayer;
    updateCell(row, col);
    
    if (checkWin(row, col)) {
        gameOver = true;
        showWinner();
        createFireworks();
        return;
    }
    
    if (checkDraw()) {
        gameOver = true;
        showDraw();
        return;
    }
    
    currentPlayer = currentPlayer === PLAYER1 ? PLAYER2 : PLAYER1;
    updatePlayerIndicator();
}

function getAvailableRow(col) {
    for (let r = ROWS - 1; r >= 0; r--) {
        if (board[r][col] === EMPTY) {
            return r;
        }
    }
    return -1;
}

function updateCell(row, col) {
    const cells = document.querySelectorAll('.cell');
    const index = row * COLS + col;
    const cell = cells[index];
    
    const disc = document.createElement('div');
    disc.className = `disc player${currentPlayer}`;
    disc.style.animation = 'dropIn 0.5s ease-in-out';
    cell.appendChild(disc);
}

function checkWin(row, col) {
    return checkDirection(row, col, 0, 1) || // Horizontal
           checkDirection(row, col, 1, 0) || // Vertical
           checkDirection(row, col, 1, 1) || // Diagonal \
           checkDirection(row, col, 1, -1);  // Diagonal /
}

function checkDirection(row, col, deltaRow, deltaCol) {
    const player = board[row][col];
    let count = 1;
    
    // Check positive direction
    let r = row + deltaRow;
    let c = col + deltaCol;
    while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board[r][c] === player) {
        count++;
        r += deltaRow;
        c += deltaCol;
    }
    
    // Check negative direction
    r = row - deltaRow;
    c = col - deltaCol;
    while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board[r][c] === player) {
        count++;
        r -= deltaRow;
        c -= deltaCol;
    }
    
    return count >= 4;
}

function checkDraw() {
    for (let c = 0; c < COLS; c++) {
        if (board[0][c] === EMPTY) {
            return false;
        }
    }
    return true;
}

function updatePlayerIndicator() {
    const indicator = document.getElementById('current-player');
    indicator.textContent = `Player ${currentPlayer}'s Turn`;
    indicator.className = `player${currentPlayer}-text`;
}

function showWinner() {
    const winnerMessage = document.getElementById('winner-message');
    winnerMessage.textContent = `🔥 Player ${currentPlayer} Wins! 🔥`;
    winnerMessage.className = `winner-message player${currentPlayer}-text`;
    winnerMessage.classList.remove('hidden');
}

function showDraw() {
    const winnerMessage = document.getElementById('winner-message');
    winnerMessage.textContent = '🔥 It\'s a Draw! 🔥';
    winnerMessage.className = 'winner-message';
    winnerMessage.classList.remove('hidden');
}

function createFireworks() {
    const particlesContainer = document.getElementById('fire-particles');
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const particle = document.createElement('div');
            particle.className = 'fire-particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 2 + 's';
            particlesContainer.appendChild(particle);
            
            setTimeout(() => particle.remove(), 3000);
        }, i * 50);
    }
}

function resetGame() {
    gameOver = false;
    currentPlayer = PLAYER1;
    initializeBoard();
    createBoardElement();
    updatePlayerIndicator();
    document.getElementById('winner-message').classList.add('hidden');
    document.getElementById('fire-particles').innerHTML = '';
}

// Initialize game
document.addEventListener('DOMContentLoaded', () => {
    initializeBoard();
    createBoardElement();
    updatePlayerIndicator();
    
    document.getElementById('reset-btn').addEventListener('click', resetGame);
});

// Create ambient fire particles
function createAmbientFireParticles() {
    const particlesContainer = document.getElementById('fire-particles');
    setInterval(() => {
        if (gameOver) return;
        
        const particle = document.createElement('div');
        particle.className = 'ambient-fire-particle';
        particle.style.left = Math.random() * 100 + '%';
        particlesContainer.appendChild(particle);
        
        setTimeout(() => particle.remove(), 4000);
    }, 500);
}

createAmbientFireParticles();