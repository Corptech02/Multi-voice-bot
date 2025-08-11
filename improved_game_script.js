// Stage-based enemy types
function getEnemyTypes() {
    const stage = Math.floor((game.currentLevel - 1) / 5) + 1;
    return {
        walker: stage === 1 ? {
            name: 'Goblin',
            width: 30,
            height: 30,
            speed: 2,
            health: 100,
            damage: 10,
            behavior: 'chase',
            score: 100,
            bodyColor: '#4a7c59',
            detailColor: '#2d5016',
            eyeColor: '#ff0000'
        } : stage === 2 ? {
            name: 'Crystal Spider',
            width: 35,
            height: 25,
            speed: 2.5,
            health: 140,
            damage: 18,
            behavior: 'chase',
            score: 250,
            bodyColor: '#9370db',
            detailColor: '#7b68ee',
            eyeColor: '#00ffff'
        } : {
            name: 'Knight',
            width: 35,
            height: 45,
            speed: 2,
            health: 200,
            damage: 30,
            behavior: 'patrol',
            score: 250,
            bodyColor: '#c0c0c0',
            detailColor: '#808080',
            eyeColor: '#000000',
            patrolRange: 150
        },
        jumper: stage === 1 ? {
            name: 'Wolf',
            width: 40,
            height: 30,
            speed: 3.5,
            health: 130,
            damage: 20,
            behavior: 'jump',
            jumpPower: 14,
            jumpCooldown: 0,
            score: 150,
            bodyColor: '#666666',
            detailColor: '#4a4a4a',
            eyeColor: '#ffff00'
        } : stage === 2 ? {
            name: 'Bat',
            width: 25,
            height: 20,
            speed: 4,
            health: 80,
            damage: 8,
            behavior: 'fly',
            jumpPower: 8,
            jumpCooldown: 0,
            score: 120,
            bodyColor: '#4a4a4a',
            detailColor: '#2a2a2a',
            eyeColor: '#ff0000',
            flyPattern: true
        } : {
            name: 'Gargoyle',
            width: 45,
            height: 40,
            speed: 3,
            health: 250,
            damage: 40,
            behavior: 'swoop',
            jumpPower: 18,
            jumpCooldown: 0,
            score: 400,
            bodyColor: '#696969',
            detailColor: '#545454',
            eyeColor: '#ff0000',
            swoopPattern: true
        },
        shooter: stage === 1 ? {
            name: 'Archer',
            width: 35,
            height: 40,
            speed: 1,
            health: 120,
            damage: 15,
            behavior: 'shoot',
            range: 350,
            fireRate: 1200,
            lastShot: 0,
            score: 200,
            bodyColor: '#5d7c3a',
            detailColor: '#3e5f2b',
            eyeColor: '#ffffff',
            projectileColor: '#8b4513'
        } : stage === 2 ? {
            name: 'Crystal Golem',
            width: 50,
            height: 50,
            speed: 0.8,
            health: 300,
            damage: 25,
            behavior: 'shoot',
            range: 400,
            fireRate: 1800,
            lastShot: 0,
            score: 300,
            bodyColor: '#8b7355',
            detailColor: '#6b5d4f',
            eyeColor: '#00ffff',
            projectileColor: '#00ffff'
        } : {
            name: 'Wizard',
            width: 30,
            height: 40,
            speed: 1.5,
            health: 150,
            damage: 35,
            behavior: 'shoot',
            range: 500,
            fireRate: 1500,
            lastShot: 0,
            score: 350,
            bodyColor: '#8b008b',
            detailColor: '#4b0082',
            eyeColor: '#ffff00',
            projectileColor: '#ff00ff'
        },
        tank: {
            name: 'Iron Golem',
            width: 60,
            height: 60,
            speed: 0.5,
            health: 500,
            damage: 50,
            behavior: 'shoot',
            range: 400,
            fireRate: 2000,
            lastShot: 0,
            score: 500,
            bodyColor: '#a9a9a9',
            detailColor: '#696969',
            eyeColor: '#ff0000',
            projectileColor: '#ff6600'
        }
    };
}

function renderEnemy(ctx, enemy, stage) {
    // Different rendering based on enemy type and stage
    switch(enemy.type) {
        case 'walker':
            if (stage === 1) {
                // Goblin
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
                // Ears
                ctx.fillStyle = enemy.detailColor;
                ctx.beginPath();
                ctx.moveTo(enemy.x - 5, enemy.y + 5);
                ctx.lineTo(enemy.x - 2, enemy.y - 5);
                ctx.lineTo(enemy.x + 5, enemy.y + 5);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width + 5, enemy.y + 5);
                ctx.lineTo(enemy.x + enemy.width + 2, enemy.y - 5);
                ctx.lineTo(enemy.x + enemy.width - 5, enemy.y + 5);
                ctx.fill();
            } else if (stage === 2) {
                // Spider
                ctx.fillStyle = enemy.bodyColor;
                ctx.beginPath();
                ctx.ellipse(enemy.x + enemy.width/2, enemy.y + enemy.height/2, enemy.width/2, enemy.height/2, 0, 0, Math.PI * 2);
                ctx.fill();
                // Legs
                ctx.strokeStyle = enemy.detailColor;
                ctx.lineWidth = 2;
                for (let i = 0; i < 4; i++) {
                    const angle = (i / 4) * Math.PI - Math.PI/2;
                    ctx.beginPath();
                    ctx.moveTo(enemy.x + enemy.width/2, enemy.y + enemy.height/2);
                    ctx.lineTo(enemy.x + enemy.width/2 + Math.cos(angle) * 20, enemy.y + enemy.height/2 + Math.sin(angle) * 15);
                    ctx.stroke();
                }
            } else {
                // Knight
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x, enemy.y + 10, enemy.width, enemy.height - 10);
                // Helmet
                ctx.fillStyle = enemy.detailColor;
                ctx.fillRect(enemy.x - 2, enemy.y, enemy.width + 4, 15);
                // Sword
                ctx.fillStyle = '#d3d3d3';
                ctx.fillRect(enemy.x + enemy.width, enemy.y + 15, 5, 20);
            }
            break;
            
        case 'jumper':
            if (stage === 1) {
                // Wolf
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x + 5, enemy.y, enemy.width - 5, enemy.height);
                // Snout
                ctx.fillRect(enemy.x, enemy.y + 5, 10, 15);
                // Tail
                ctx.fillRect(enemy.x + enemy.width - 5, enemy.y + 5, 10, 10);
            } else if (stage === 2) {
                // Bat
                ctx.fillStyle = enemy.bodyColor;
                ctx.beginPath();
                ctx.ellipse(enemy.x + enemy.width/2, enemy.y + enemy.height/2, enemy.width/3, enemy.height/2, 0, 0, Math.PI * 2);
                ctx.fill();
                // Wings
                ctx.fillStyle = enemy.detailColor;
                const wingFlap = Math.sin(Date.now() * 0.01) * 0.3;
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width/2, enemy.y + enemy.height/2);
                ctx.lineTo(enemy.x - 10, enemy.y + enemy.height/2 - 10 * wingFlap);
                ctx.lineTo(enemy.x, enemy.y + enemy.height);
                ctx.lineTo(enemy.x + enemy.width/2, enemy.y + enemy.height/2);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width/2, enemy.y + enemy.height/2);
                ctx.lineTo(enemy.x + enemy.width + 10, enemy.y + enemy.height/2 - 10 * wingFlap);
                ctx.lineTo(enemy.x + enemy.width, enemy.y + enemy.height);
                ctx.lineTo(enemy.x + enemy.width/2, enemy.y + enemy.height/2);
                ctx.fill();
            } else {
                // Gargoyle
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x + 10, enemy.y, enemy.width - 20, enemy.height);
                // Wings
                ctx.fillStyle = enemy.detailColor;
                ctx.beginPath();
                ctx.moveTo(enemy.x, enemy.y + 10);
                ctx.lineTo(enemy.x + 10, enemy.y);
                ctx.lineTo(enemy.x + 10, enemy.y + 30);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width, enemy.y + 10);
                ctx.lineTo(enemy.x + enemy.width - 10, enemy.y);
                ctx.lineTo(enemy.x + enemy.width - 10, enemy.y + 30);
                ctx.fill();
                // Horns
                ctx.fillStyle = enemy.bodyColor;
                ctx.beginPath();
                ctx.moveTo(enemy.x + 12, enemy.y);
                ctx.lineTo(enemy.x + 8, enemy.y - 8);
                ctx.lineTo(enemy.x + 16, enemy.y);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width - 12, enemy.y);
                ctx.lineTo(enemy.x + enemy.width - 8, enemy.y - 8);
                ctx.lineTo(enemy.x + enemy.width - 16, enemy.y);
                ctx.fill();
            }
            break;
            
        case 'shooter':
            if (stage === 1) {
                // Archer
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
                // Bow
                ctx.strokeStyle = enemy.detailColor;
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(enemy.x - 5, enemy.y + enemy.height/2, 15, -Math.PI/3, Math.PI/3, false);
                ctx.stroke();
                // Hood
                ctx.fillStyle = enemy.detailColor;
                ctx.beginPath();
                ctx.moveTo(enemy.x, enemy.y);
                ctx.lineTo(enemy.x + enemy.width/2, enemy.y - 5);
                ctx.lineTo(enemy.x + enemy.width, enemy.y);
                ctx.lineTo(enemy.x + enemy.width, enemy.y + 10);
                ctx.lineTo(enemy.x, enemy.y + 10);
                ctx.fill();
            } else if (stage === 2) {
                // Crystal Golem
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x + 5, enemy.y + 5, enemy.width - 10, enemy.height - 10);
                // Crystal formations
                ctx.fillStyle = enemy.eyeColor;
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width/2, enemy.y);
                ctx.lineTo(enemy.x + enemy.width/2 - 10, enemy.y + 10);
                ctx.lineTo(enemy.x + enemy.width/2 + 10, enemy.y + 10);
                ctx.fill();
                // Rocky texture
                ctx.strokeStyle = enemy.detailColor;
                ctx.lineWidth = 2;
                ctx.strokeRect(enemy.x + 5, enemy.y + 5, enemy.width - 10, enemy.height - 10);
            } else {
                // Wizard
                ctx.fillStyle = enemy.bodyColor;
                ctx.fillRect(enemy.x, enemy.y + 5, enemy.width, enemy.height - 5);
                // Hat
                ctx.fillStyle = enemy.detailColor;
                ctx.beginPath();
                ctx.moveTo(enemy.x + enemy.width/2, enemy.y - 10);
                ctx.lineTo(enemy.x - 5, enemy.y + 10);
                ctx.lineTo(enemy.x + enemy.width + 5, enemy.y + 10);
                ctx.fill();
                // Staff
                ctx.fillStyle = '#8b4513';
                ctx.fillRect(enemy.x + enemy.width, enemy.y + 10, 3, 25);
                ctx.fillStyle = enemy.projectileColor;
                ctx.beginPath();
                ctx.arc(enemy.x + enemy.width + 1.5, enemy.y + 8, 5, 0, Math.PI * 2);
                ctx.fill();
            }
            break;
            
        case 'tank':
            // Iron Golem (Castle only)
            ctx.fillStyle = enemy.bodyColor;
            ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
            // Metal plating
            ctx.strokeStyle = enemy.detailColor;
            ctx.lineWidth = 3;
            ctx.strokeRect(enemy.x + 5, enemy.y + 5, enemy.width - 10, enemy.height - 10);
            ctx.strokeRect(enemy.x + 10, enemy.y + 10, enemy.width - 20, enemy.height - 20);
            // Rivets
            ctx.fillStyle = enemy.detailColor;
            for (let i = 0; i < 4; i++) {
                for (let j = 0; j < 4; j++) {
                    ctx.beginPath();
                    ctx.arc(enemy.x + 15 + i * 10, enemy.y + 15 + j * 10, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
            break;
    }
    
    // Eyes for all enemies
    ctx.fillStyle = enemy.eyeColor;
    if (enemy.type !== 'tank') {
        ctx.fillRect(enemy.x + 5, enemy.y + 10, 5, 5);
        ctx.fillRect(enemy.x + enemy.width - 10, enemy.y + 10, 5, 5);
    } else {
        // Glowing eyes for tank
        ctx.shadowBlur = 10;
        ctx.shadowColor = enemy.eyeColor;
        ctx.fillRect(enemy.x + 20, enemy.y + 20, 8, 8);
        ctx.fillRect(enemy.x + enemy.width - 28, enemy.y + 20, 8, 8);
        ctx.shadowBlur = 0;
    }
    
    // Health bar
    if (enemy.health < enemy.maxHealth) {
        ctx.fillStyle = '#000';
        ctx.fillRect(enemy.x - 5, enemy.y - 15, enemy.width + 10, 8);
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(enemy.x - 3, enemy.y - 13, (enemy.width + 6) * (enemy.health / enemy.maxHealth), 4);
    }
}

// Enhanced enemy behaviors
function enhancedEnemyBehaviors(enemy, dx, dy, dist) {
    switch(enemy.behavior) {
        case 'patrol':
            // Knight patrol behavior
            if (Math.abs(enemy.x - enemy.originalX) > enemy.patrolRange) {
                enemy.patrolDirection *= -1;
            }
            enemy.vx = enemy.patrolDirection * enemy.speed;
            
            // Attack if player is close
            if (Math.abs(dx) < 100 && Math.abs(dy) < 50) {
                enemy.vx = Math.sign(dx) * enemy.speed * 1.5;
            }
            
            // Edge detection
            if (enemy.onGround) {
                const checkX = enemy.x + (enemy.vx > 0 ? enemy.width : 0) + enemy.vx * 5;
                const checkY = enemy.y + enemy.height + 10;
                let onPlatform = false;
                
                for (const platform of level.platforms) {
                    if (checkX >= platform.x && checkX <= platform.x + platform.width &&
                        checkY >= platform.y && checkY <= platform.y + platform.height) {
                        onPlatform = true;
                        break;
                    }
                }
                
                if (!onPlatform) {
                    enemy.patrolDirection *= -1;
                    enemy.vx = enemy.patrolDirection * enemy.speed;
                }
            }
            break;
            
        case 'fly':
            // Bat flying pattern
            enemy.flyTime += 0.05;
            enemy.y = enemy.baseY + Math.sin(enemy.flyTime) * 30;
            
            if (Math.abs(dx) > 20) {
                enemy.vx = Math.sign(dx) * enemy.speed;
            } else {
                enemy.vx *= 0.9;
            }
            
            // No gravity for flying enemies
            enemy.vy = 0;
            break;
            
        case 'swoop':
            // Gargoyle swoop behavior
            if (!enemy.swooping && enemy.swoopCooldown <= 0 && dist < 300) {
                enemy.swooping = true;
                enemy.swoopCooldown = 120;
            }
            
            if (enemy.swooping) {
                enemy.vx = Math.sign(dx) * enemy.speed * 2;
                enemy.vy = Math.sign(dy) * enemy.speed;
                
                if (dist < 50 || enemy.onGround) {
                    enemy.swooping = false;
                    enemy.vy = -10;
                }
            } else {
                if (Math.abs(dx) > 100) {
                    enemy.vx = Math.sign(dx) * enemy.speed * 0.5;
                } else {
                    enemy.vx *= 0.8;
                }
                
                if (enemy.onGround && Math.random() < 0.02) {
                    enemy.vy = -enemy.jumpPower;
                }
            }
            
            if (enemy.swoopCooldown > 0) enemy.swoopCooldown--;
            break;
    }
}

// Enhanced stage themes
function getStageTheme(stage) {
    const themes = {
        1: { // Forest
            sky1: '#87CEEB',
            sky2: '#98FB98',
            groundColor: '#2d5016',
            platformColor: '#5d7c3a',
            decorColor: '#228B22'
        },
        2: { // Cave
            sky1: '#1a1a2e',
            sky2: '#16213e',
            groundColor: '#3e3e3e',
            platformColor: '#5a5a5a',
            decorColor: '#00ffff'
        },
        3: { // Castle
            sky1: '#2c2c54',
            sky2: '#474787',
            groundColor: '#4a3c3c',
            platformColor: '#8b6969',
            decorColor: '#ffd700'
        }
    };
    
    return themes[stage] || themes[1];
}

// Enhanced level generation with consistent stage themes
function generateStage1Level(levelNum) {
    level.width = 4000 + levelNum * 1000;
    
    // Starting platform
    level.platforms.push({ x: 0, y: 650, width: 400, height: 50 });
    
    // Generate forest-themed platforms
    let x = 500;
    while (x < level.width - 500) {
        const width = 150 + Math.random() * 200;
        const height = 20;
        const y = 450 + Math.random() * 200;
        
        level.platforms.push({ x, y, width, height });
        
        // Add forest enemies
        if (Math.random() > 0.5) {
            const enemyType = ['walker', 'jumper', 'shooter'][Math.floor(Math.random() * 3)];
            level.enemySpawns.push({ x: x + width/2, y: y - 50, type: enemyType });
        }
        
        // Add trees and bushes
        if (Math.random() > 0.3) {
            level.decorations = level.decorations || [];
            level.decorations.push({
                type: 'tree',
                x: x + Math.random() * width,
                y: y
            });
        }
        
        x += width + 100 + Math.random() * 200;
    }
    
    // End platform
    level.platforms.push({ x: level.width - 500, y: 650, width: 500, height: 50 });
    
    // Add weapons
    for (let i = 0; i < 3 + levelNum; i++) {
        const weaponType = ['pistol', 'shotgun', 'rifle'][Math.floor(Math.random() * 3)];
        level.weaponPickups.push({
            x: 500 + Math.random() * (level.width - 1000),
            y: 400,
            type: weaponType,
            taken: false
        });
    }
    
    // Add pickups
    for (let i = 0; i < 10 + levelNum * 5; i++) {
        const pickupType = ['health', 'speed', 'weaponPower'][Math.floor(Math.random() * 3)];
        level.pickups.push({
            x: 300 + Math.random() * (level.width - 600),
            y: 300 + Math.random() * 200,
            type: pickupType,
            active: true
        });
    }
}

function generateStage2Level(levelNum) {
    level.width = 5000 + levelNum * 1500;
    
    // Cave-themed vertical level
    level.platforms.push({ x: 0, y: 650, width: 300, height: 50 });
    
    let x = 400;
    let y = 650;
    
    while (x < level.width - 500) {
        // Create vertical cave sections with stalactites
        for (let i = 0; i < 3 + levelNum; i++) {
            y -= 120;
            const width = 100 + Math.random() * 100;
            level.platforms.push({ x: x + i * 50, y, width, height: 20 });
            
            // Add crystals
            if (Math.random() > 0.4) {
                level.decorations = level.decorations || [];
                level.decorations.push({
                    type: 'crystal',
                    x: x + i * 50 + width/2,
                    y: y - 20
                });
            }
            
            if (Math.random() > 0.6) {
                level.enemySpawns.push({
                    x: x + i * 50 + width/2,
                    y: y - 50,
                    type: ['walker', 'jumper', 'shooter'][Math.floor(Math.random() * 3)]
                });
            }
        }
        
        x += 400 + Math.random() * 300;
        y = 650;
    }
    
    level.platforms.push({ x: level.width - 500, y: 650, width: 500, height: 50 });
}

function generateStage3Level(levelNum) {
    level.width = 6000 + levelNum * 2000;
    
    // Castle-themed with moving platforms
    level.platforms.push({ x: 0, y: 650, width: 400, height: 50 });
    
    let x = 500;
    while (x < level.width - 500) {
        const width = 120 + Math.random() * 150;
        const height = 20;
        const y = 500 + Math.random() * 150;
        
        const platform = { x, y, width, height };
        
        // Moving platforms
        if (Math.random() > 0.6) {
            platform.moving = true;
            platform.moveRange = 100;
            platform.moveSpeed = 1 + Math.random();
            platform.moveDirection = 1;
            platform.originalX = x;
        }
        
        level.platforms.push(platform);
        
        // Castle enemies and decorations
        if (Math.random() > 0.4) {
            const enemyType = ['walker', 'jumper', 'shooter', 'tank'][Math.floor(Math.random() * 4)];
            level.enemySpawns.push({ x: x + width/2, y: y - 50, type: enemyType });
        }
        
        // Castle banners and torches
        if (Math.random() > 0.5) {
            level.decorations = level.decorations || [];
            level.decorations.push({
                type: 'banner',
                x: x + width/2,
                y: y - 50
            });
        }
        
        x += width + 150 + Math.random() * 200;
    }
    
    level.platforms.push({ x: level.width - 500, y: 650, width: 500, height: 50 });
    
    // Add more tank enemies
    for (let i = 0; i < levelNum * 2; i++) {
        level.enemySpawns.push({
            x: 1000 + Math.random() * (level.width - 2000),
            y: 600,
            type: 'tank'
        });
    }
}