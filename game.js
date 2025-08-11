// Game constants
const CANVAS_WIDTH = 960;
const CANVAS_HEIGHT = 720;
const ROOM_WIDTH = 800;
const ROOM_HEIGHT = 600;
const ROOM_OFFSET_X = (CANVAS_WIDTH - ROOM_WIDTH) / 2;
const ROOM_OFFSET_Y = (CANVAS_HEIGHT - ROOM_HEIGHT) / 2;

// Get canvas and context
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// Game state
const game = {
    state: 'playing',
    currentRoom: null,
    rooms: [],
    doors: []
};

// Player object
const player = {
    x: CANVAS_WIDTH / 2,
    y: CANVAS_HEIGHT / 2,
    radius: 15,
    speed: 4,
    health: 6,
    maxHealth: 6,
    tearDamage: 1,
    tearRate: 500, // milliseconds between shots
    tearSpeed: 8,
    tearRange: 250,
    lastShot: 0,
    invulnerable: false,
    invulnerableTime: 0,
    invulnerableDuration: 1000
};

// Input handling
const keys = {};
const mouse = { x: 0, y: 0 };

// Game objects arrays
const tears = [];
const enemies = [];
const items = [];
const pickups = [];

// Input event listeners
document.addEventListener('keydown', (e) => {
    keys[e.key.toLowerCase()] = true;
});

document.addEventListener('keyup', (e) => {
    keys[e.key.toLowerCase()] = false;
});

canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
});

canvas.addEventListener('click', (e) => {
    shootTear();
});

// Tear class
class Tear {
    constructor(x, y, vx, vy, damage) {
        this.x = x;
        this.y = y;
        this.vx = vx;
        this.vy = vy;
        this.radius = 5;
        this.damage = damage;
        this.distanceTraveled = 0;
        this.maxDistance = player.tearRange;
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;
        this.distanceTraveled += Math.sqrt(this.vx * this.vx + this.vy * this.vy);
        
        // Check if tear has exceeded its range
        if (this.distanceTraveled > this.maxDistance) {
            return false;
        }
        
        // Check room boundaries
        if (this.x < ROOM_OFFSET_X + this.radius || 
            this.x > ROOM_OFFSET_X + ROOM_WIDTH - this.radius ||
            this.y < ROOM_OFFSET_Y + this.radius || 
            this.y > ROOM_OFFSET_Y + ROOM_HEIGHT - this.radius) {
            return false;
        }
        
        return true;
    }

    draw() {
        ctx.fillStyle = '#4FC3F7';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
        
        // Add teardrop effect
        ctx.fillStyle = '#81D4FA';
        ctx.beginPath();
        ctx.arc(this.x - this.vx * 0.5, this.y - this.vy * 0.5, this.radius * 0.7, 0, Math.PI * 2);
        ctx.fill();
    }
}

// Enemy class
class Enemy {
    constructor(x, y, type = 'basic') {
        this.x = x;
        this.y = y;
        this.type = type;
        this.radius = 20;
        this.speed = 1.5;
        this.health = 3;
        this.maxHealth = 3;
        this.damage = 1;
        this.knockback = 0;
        this.knockbackX = 0;
        this.knockbackY = 0;
    }

    update() {
        // Apply knockback
        if (this.knockback > 0) {
            this.x += this.knockbackX;
            this.y += this.knockbackY;
            this.knockback *= 0.9;
            if (this.knockback < 0.1) {
                this.knockback = 0;
            }
        } else {
            // Basic AI - move towards player
            const dx = player.x - this.x;
            const dy = player.y - this.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance > 0) {
                this.x += (dx / distance) * this.speed;
                this.y += (dy / distance) * this.speed;
            }
        }
        
        // Keep enemy within room bounds
        this.x = Math.max(ROOM_OFFSET_X + this.radius, 
                 Math.min(ROOM_OFFSET_X + ROOM_WIDTH - this.radius, this.x));
        this.y = Math.max(ROOM_OFFSET_Y + this.radius, 
                 Math.min(ROOM_OFFSET_Y + ROOM_HEIGHT - this.radius, this.y));
    }

    takeDamage(damage, fromX, fromY) {
        this.health -= damage;
        
        // Apply knockback
        const dx = this.x - fromX;
        const dy = this.y - fromY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
            this.knockback = 10;
            this.knockbackX = (dx / distance) * this.knockback;
            this.knockbackY = (dy / distance) * this.knockback;
        }
        
        if (this.health <= 0) {
            // Chance to drop pickup
            if (Math.random() < 0.3) {
                pickups.push(new Pickup(this.x, this.y, Math.random() < 0.7 ? 'heart' : 'coin'));
            }
            return true; // Enemy is dead
        }
        return false;
    }

    draw() {
        // Draw enemy based on type
        if (this.type === 'basic') {
            // Main body
            ctx.fillStyle = '#8B4513';
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fill();
            
            // Eyes
            ctx.fillStyle = 'red';
            ctx.beginPath();
            ctx.arc(this.x - 7, this.y - 5, 3, 0, Math.PI * 2);
            ctx.arc(this.x + 7, this.y - 5, 3, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Health bar
        if (this.health < this.maxHealth) {
            ctx.fillStyle = 'red';
            ctx.fillRect(this.x - 20, this.y - 30, 40 * (this.health / this.maxHealth), 4);
            ctx.strokeStyle = 'white';
            ctx.strokeRect(this.x - 20, this.y - 30, 40, 4);
        }
    }
}

// Pickup class
class Pickup {
    constructor(x, y, type) {
        this.x = x;
        this.y = y;
        this.type = type;
        this.radius = 10;
        this.bobOffset = Math.random() * Math.PI * 2;
    }

    update() {
        // Check if player picks it up
        const dx = player.x - this.x;
        const dy = player.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < player.radius + this.radius) {
            if (this.type === 'heart' && player.health < player.maxHealth) {
                player.health++;
                updateHealthDisplay();
                return false;
            } else if (this.type === 'coin') {
                // TODO: Implement coin system
                return false;
            }
        }
        return true;
    }

    draw() {
        const bobY = Math.sin(Date.now() / 200 + this.bobOffset) * 3;
        
        if (this.type === 'heart') {
            ctx.fillStyle = 'red';
            ctx.save();
            ctx.translate(this.x, this.y + bobY);
            ctx.scale(0.8, 0.8);
            ctx.beginPath();
            ctx.moveTo(0, -5);
            ctx.bezierCurveTo(-5, -10, -10, -8, -10, -4);
            ctx.bezierCurveTo(-10, 0, -5, 5, 0, 10);
            ctx.bezierCurveTo(5, 5, 10, 0, 10, -4);
            ctx.bezierCurveTo(10, -8, 5, -10, 0, -5);
            ctx.fill();
            ctx.restore();
        } else if (this.type === 'coin') {
            ctx.fillStyle = 'gold';
            ctx.beginPath();
            ctx.arc(this.x, this.y + bobY, this.radius, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = 'orange';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('¢', this.x, this.y + bobY);
        }
    }
}

// Power-up/Item class
class Item {
    constructor(x, y, effect) {
        this.x = x;
        this.y = y;
        this.effect = effect;
        this.radius = 15;
        this.bobOffset = Math.random() * Math.PI * 2;
    }

    applyEffect() {
        switch(this.effect.type) {
            case 'damage_up':
                player.tearDamage += 0.5;
                break;
            case 'tears_up':
                player.tearRate *= 0.8; // Decrease time between shots
                break;
            case 'speed_up':
                player.speed += 1;
                break;
            case 'range_up':
                player.tearRange += 50;
                break;
            case 'health_up':
                player.maxHealth += 2;
                player.health += 2;
                updateHealthDisplay();
                break;
        }
    }

    draw() {
        const bobY = Math.sin(Date.now() / 200 + this.bobOffset) * 5;
        
        // Pedestal
        ctx.fillStyle = '#666';
        ctx.fillRect(this.x - 20, this.y + 10, 40, 10);
        
        // Item glow
        ctx.shadowBlur = 20;
        ctx.shadowColor = 'yellow';
        
        // Item based on type
        ctx.fillStyle = '#FFD700';
        ctx.beginPath();
        ctx.arc(this.x, this.y + bobY, this.radius, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.shadowBlur = 0;
        
        // Item icon
        ctx.fillStyle = '#333';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        switch(this.effect.type) {
            case 'damage_up':
                ctx.fillText('↑', this.x, this.y + bobY);
                break;
            case 'tears_up':
                ctx.fillText('💧', this.x, this.y + bobY);
                break;
            case 'speed_up':
                ctx.fillText('⚡', this.x, this.y + bobY);
                break;
            case 'range_up':
                ctx.fillText('→', this.x, this.y + bobY);
                break;
            case 'health_up':
                ctx.fillText('♥', this.x, this.y + bobY);
                break;
        }
    }
}

// Room class
class Room {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.cleared = false;
        this.visited = false;
        this.doors = {
            top: false,
            bottom: false,
            left: false,
            right: false
        };
        this.enemyCount = Math.floor(Math.random() * 4) + 2;
        this.hasItem = Math.random() < 0.3;
    }

    enter() {
        this.visited = true;
        enemies.length = 0;
        items.length = 0;
        tears.length = 0;
        pickups.length = 0;
        
        if (!this.cleared) {
            // Spawn enemies
            for (let i = 0; i < this.enemyCount; i++) {
                const angle = (Math.PI * 2 * i) / this.enemyCount;
                const dist = 150;
                enemies.push(new Enemy(
                    CANVAS_WIDTH / 2 + Math.cos(angle) * dist,
                    CANVAS_HEIGHT / 2 + Math.sin(angle) * dist
                ));
            }
        } else if (this.hasItem && this.cleared) {
            // Spawn item in cleared room
            const itemTypes = ['damage_up', 'tears_up', 'speed_up', 'range_up', 'health_up'];
            const randomType = itemTypes[Math.floor(Math.random() * itemTypes.length)];
            items.push(new Item(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2, { type: randomType }));
        }
    }
}

// Initialize game
function init() {
    // Create starting room
    const startRoom = new Room(0, 0);
    startRoom.doors.right = true;
    game.currentRoom = startRoom;
    game.rooms.push(startRoom);
    
    // Create a few connected rooms
    const room2 = new Room(1, 0);
    room2.doors.left = true;
    room2.doors.bottom = true;
    game.rooms.push(room2);
    
    const room3 = new Room(1, 1);
    room3.doors.top = true;
    game.rooms.push(room3);
    
    // Enter the starting room
    game.currentRoom.enter();
    
    updateHealthDisplay();
    gameLoop();
}

// Shooting mechanics
function shootTear() {
    const now = Date.now();
    if (now - player.lastShot < player.tearRate) return;
    
    const dx = mouse.x - player.x;
    const dy = mouse.y - player.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    if (distance > 0) {
        const vx = (dx / distance) * player.tearSpeed;
        const vy = (dy / distance) * player.tearSpeed;
        tears.push(new Tear(player.x, player.y, vx, vy, player.tearDamage));
        player.lastShot = now;
    }
}

// Alternative shooting with arrow keys
function shootWithArrows() {
    const now = Date.now();
    if (now - player.lastShot < player.tearRate) return;
    
    let vx = 0, vy = 0;
    
    if (keys['arrowup']) vy = -player.tearSpeed;
    else if (keys['arrowdown']) vy = player.tearSpeed;
    else if (keys['arrowleft']) vx = -player.tearSpeed;
    else if (keys['arrowright']) vx = player.tearSpeed;
    
    if (vx !== 0 || vy !== 0) {
        tears.push(new Tear(player.x, player.y, vx, vy, player.tearDamage));
        player.lastShot = now;
    }
}

// Update game state
function update() {
    // Player movement
    let dx = 0, dy = 0;
    if (keys['w']) dy -= player.speed;
    if (keys['s']) dy += player.speed;
    if (keys['a']) dx -= player.speed;
    if (keys['d']) dx += player.speed;
    
    // Normalize diagonal movement
    if (dx !== 0 && dy !== 0) {
        const factor = 0.707; // 1/sqrt(2)
        dx *= factor;
        dy *= factor;
    }
    
    player.x += dx;
    player.y += dy;
    
    // Keep player within room bounds
    player.x = Math.max(ROOM_OFFSET_X + player.radius, 
                Math.min(ROOM_OFFSET_X + ROOM_WIDTH - player.radius, player.x));
    player.y = Math.max(ROOM_OFFSET_Y + player.radius, 
                Math.min(ROOM_OFFSET_Y + ROOM_HEIGHT - player.radius, player.y));
    
    // Check for arrow key shooting
    shootWithArrows();
    
    // Update invulnerability
    if (player.invulnerable) {
        player.invulnerableTime -= 16; // Assuming 60 FPS
        if (player.invulnerableTime <= 0) {
            player.invulnerable = false;
        }
    }
    
    // Update tears
    for (let i = tears.length - 1; i >= 0; i--) {
        if (!tears[i].update()) {
            tears.splice(i, 1);
        }
    }
    
    // Update enemies
    for (let i = enemies.length - 1; i >= 0; i--) {
        enemies[i].update();
        
        // Check collision with player
        if (!player.invulnerable) {
            const dx = player.x - enemies[i].x;
            const dy = player.y - enemies[i].y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < player.radius + enemies[i].radius) {
                player.health -= enemies[i].damage;
                player.invulnerable = true;
                player.invulnerableTime = player.invulnerableDuration;
                updateHealthDisplay();
                
                if (player.health <= 0) {
                    game.state = 'gameover';
                }
            }
        }
    }
    
    // Update pickups
    for (let i = pickups.length - 1; i >= 0; i--) {
        if (!pickups[i].update()) {
            pickups.splice(i, 1);
        }
    }
    
    // Check tear-enemy collisions
    for (let i = tears.length - 1; i >= 0; i--) {
        for (let j = enemies.length - 1; j >= 0; j--) {
            const dx = tears[i].x - enemies[j].x;
            const dy = tears[i].y - enemies[j].y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < tears[i].radius + enemies[j].radius) {
                if (enemies[j].takeDamage(tears[i].damage, tears[i].x, tears[i].y)) {
                    enemies.splice(j, 1);
                }
                tears.splice(i, 1);
                break;
            }
        }
    }
    
    // Check item pickup
    for (let i = items.length - 1; i >= 0; i--) {
        const dx = player.x - items[i].x;
        const dy = player.y - items[i].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < player.radius + items[i].radius) {
            items[i].applyEffect();
            items.splice(i, 1);
            updateStats();
        }
    }
    
    // Check if room is cleared
    if (enemies.length === 0 && !game.currentRoom.cleared) {
        game.currentRoom.cleared = true;
        if (game.currentRoom.hasItem) {
            const itemTypes = ['damage_up', 'tears_up', 'speed_up', 'range_up', 'health_up'];
            const randomType = itemTypes[Math.floor(Math.random() * itemTypes.length)];
            items.push(new Item(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2, { type: randomType }));
        }
    }
    
    // Check door transitions
    checkDoorTransitions();
}

// Check if player is entering a door
function checkDoorTransitions() {
    const doorWidth = 60;
    const doorHeight = 60;
    
    // Top door
    if (game.currentRoom.doors.top && 
        player.x > CANVAS_WIDTH/2 - doorWidth/2 && 
        player.x < CANVAS_WIDTH/2 + doorWidth/2 &&
        player.y < ROOM_OFFSET_Y + player.radius) {
        transitionRoom(0, -1);
    }
    
    // Bottom door
    if (game.currentRoom.doors.bottom && 
        player.x > CANVAS_WIDTH/2 - doorWidth/2 && 
        player.x < CANVAS_WIDTH/2 + doorWidth/2 &&
        player.y > ROOM_OFFSET_Y + ROOM_HEIGHT - player.radius) {
        transitionRoom(0, 1);
    }
    
    // Left door
    if (game.currentRoom.doors.left && 
        player.y > CANVAS_HEIGHT/2 - doorWidth/2 && 
        player.y < CANVAS_HEIGHT/2 + doorWidth/2 &&
        player.x < ROOM_OFFSET_X + player.radius) {
        transitionRoom(-1, 0);
    }
    
    // Right door
    if (game.currentRoom.doors.right && 
        player.y > CANVAS_HEIGHT/2 - doorWidth/2 && 
        player.y < CANVAS_HEIGHT/2 + doorWidth/2 &&
        player.x > ROOM_OFFSET_X + ROOM_WIDTH - player.radius) {
        transitionRoom(1, 0);
    }
}

// Transition to another room
function transitionRoom(dx, dy) {
    const newX = game.currentRoom.x + dx;
    const newY = game.currentRoom.y + dy;
    
    // Find the room at the new position
    let newRoom = game.rooms.find(room => room.x === newX && room.y === newY);
    
    if (newRoom) {
        game.currentRoom = newRoom;
        
        // Position player at opposite door
        if (dx === 1) player.x = ROOM_OFFSET_X + player.radius * 2;
        else if (dx === -1) player.x = ROOM_OFFSET_X + ROOM_WIDTH - player.radius * 2;
        else if (dy === 1) player.y = ROOM_OFFSET_Y + player.radius * 2;
        else if (dy === -1) player.y = ROOM_OFFSET_Y + ROOM_HEIGHT - player.radius * 2;
        
        newRoom.enter();
    }
}

// Drawing functions
function drawRoom() {
    // Room background
    ctx.fillStyle = '#3a3a3a';
    ctx.fillRect(ROOM_OFFSET_X, ROOM_OFFSET_Y, ROOM_WIDTH, ROOM_HEIGHT);
    
    // Room border
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 10;
    ctx.strokeRect(ROOM_OFFSET_X, ROOM_OFFSET_Y, ROOM_WIDTH, ROOM_HEIGHT);
    
    // Draw doors
    const doorWidth = 60;
    const doorHeight = 60;
    
    if (game.currentRoom.doors.top) {
        ctx.fillStyle = game.currentRoom.cleared ? '#4a4a4a' : '#2a2a2a';
        ctx.fillRect(CANVAS_WIDTH/2 - doorWidth/2, ROOM_OFFSET_Y - 5, doorWidth, 15);
    }
    
    if (game.currentRoom.doors.bottom) {
        ctx.fillStyle = game.currentRoom.cleared ? '#4a4a4a' : '#2a2a2a';
        ctx.fillRect(CANVAS_WIDTH/2 - doorWidth/2, ROOM_OFFSET_Y + ROOM_HEIGHT - 10, doorWidth, 15);
    }
    
    if (game.currentRoom.doors.left) {
        ctx.fillStyle = game.currentRoom.cleared ? '#4a4a4a' : '#2a2a2a';
        ctx.fillRect(ROOM_OFFSET_X - 5, CANVAS_HEIGHT/2 - doorHeight/2, 15, doorHeight);
    }
    
    if (game.currentRoom.doors.right) {
        ctx.fillStyle = game.currentRoom.cleared ? '#4a4a4a' : '#2a2a2a';
        ctx.fillRect(ROOM_OFFSET_X + ROOM_WIDTH - 10, CANVAS_HEIGHT/2 - doorHeight/2, 15, doorHeight);
    }
}

function drawPlayer() {
    // Flash when invulnerable
    if (player.invulnerable && Math.floor(Date.now() / 100) % 2) {
        ctx.globalAlpha = 0.5;
    }
    
    // Body
    ctx.fillStyle = '#FFB6C1';
    ctx.beginPath();
    ctx.arc(player.x, player.y, player.radius, 0, Math.PI * 2);
    ctx.fill();
    
    // Head (slightly offset upward)
    ctx.fillStyle = '#FFB6C1';
    ctx.beginPath();
    ctx.arc(player.x, player.y - 10, player.radius * 0.8, 0, Math.PI * 2);
    ctx.fill();
    
    // Eyes (crying)
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.arc(player.x - 5, player.y - 10, 2, 0, Math.PI * 2);
    ctx.arc(player.x + 5, player.y - 10, 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Tears streaming down
    ctx.strokeStyle = '#4FC3F7';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(player.x - 5, player.y - 8);
    ctx.lineTo(player.x - 5, player.y - 2);
    ctx.moveTo(player.x + 5, player.y - 8);
    ctx.lineTo(player.x + 5, player.y - 2);
    ctx.stroke();
    
    ctx.globalAlpha = 1;
}

function render() {
    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    
    // Draw a border to show canvas is working
    ctx.strokeStyle = 'green';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    
    if (game.state === 'playing') {
        // Check if currentRoom exists
        if (!game.currentRoom) {
            ctx.fillStyle = 'red';
            ctx.font = '24px Arial';
            ctx.fillText('ERROR: No current room!', 100, 100);
            return;
        }
        
        // Draw room
        drawRoom();
        
        // Draw pickups
        pickups.forEach(pickup => pickup.draw());
        
        // Draw items
        items.forEach(item => item.draw());
        
        // Draw enemies
        enemies.forEach(enemy => enemy.draw());
        
        // Draw player
        drawPlayer();
        
        // Draw tears
        tears.forEach(tear => tear.draw());
    } else if (game.state === 'gameover') {
        ctx.fillStyle = 'white';
        ctx.font = '48px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('GAME OVER', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);
        ctx.font = '24px Arial';
        ctx.fillText('Refresh to restart', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 50);
    }
}

// Update UI
function updateHealthDisplay() {
    const healthDiv = document.getElementById('healthDisplay');
    if (!healthDiv) {
        console.error('Health display element not found!');
        return;
    }
    healthDiv.innerHTML = '';
    
    for (let i = 0; i < player.maxHealth; i++) {
        const heart = document.createElement('div');
        heart.className = 'heart';
        if (i < player.health) {
            heart.classList.add('full');
        } else {
            heart.classList.add('empty');
        }
        healthDiv.appendChild(heart);
    }
}

function updateStats() {
    const statsDiv = document.getElementById('stats');
    if (!statsDiv) {
        console.error('Stats display element not found!');
        return;
    }
    statsDiv.innerHTML = `
        Damage: ${player.tearDamage.toFixed(1)} | 
        Tears: ${(1000/player.tearRate).toFixed(1)}/s | 
        Speed: ${player.speed.toFixed(1)} | 
        Range: ${player.tearRange}
    `;
}

// Game loop
function gameLoop() {
    update();
    render();
    requestAnimationFrame(gameLoop);
}

// Start the game
init();
updateStats();