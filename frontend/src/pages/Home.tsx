import { motion, useScroll, useTransform } from 'framer-motion';
import { Github, Mail, Linkedin } from 'lucide-react';
import { useRef } from 'react';
import step1Img from '../assets/Step1.png';
import './Home.css';

const playerNameRows = [
  [
    "Nikola Jokic", "Giannis Antetokounmpo", "Luka Doncic", "Jayson Tatum", "Joel Embiid",
    "Stephen Curry", "Kevin Durant", "LeBron James", "Shai Gilgeous-Alexander", "Anthony Edwards",
    "Devin Booker", "Ja Morant", "Donovan Mitchell", "Tyrese Haliburton", "Jaylen Brown",
  ],
  [
    "Jimmy Butler", "Kawhi Leonard", "Paul George", "Damian Lillard", "Anthony Davis",
    "Zion Williamson", "Kyrie Irving", "James Harden", "Bam Adebayo", "Trae Young",
    "Karl-Anthony Towns", "DeMar DeRozan", "Pascal Siakam", "Jalen Brunson", "Kristaps Porzingis",
  ],
  [
    "De'Aaron Fox", "LaMelo Ball", "Darius Garland", "Tyrese Maxey", "Scottie Barnes",
    "Mikal Bridges", "Jrue Holiday", "Domantas Sabonis", "Jamal Murray", "Brandon Ingram",
    "Paolo Banchero", "Cade Cunningham", "Victor Wembanyama", "Chet Holmgren", "Franz Wagner",
  ],
];

const Home = () => {
  const heroRef = useRef(null);
  const stepsRef = useRef(null);
  const namesRef = useRef(null);

  const { scrollYProgress: namesProgress } = useScroll({
    target: namesRef,
    offset: ["start end", "end start"]
  });

  const row1X = useTransform(namesProgress, [0, 1], ['5%', '-15%']);
  const row2X = useTransform(namesProgress, [0, 1], ['-15%', '5%']);
  const row3X = useTransform(namesProgress, [0, 1], ['5%', '-15%']);

  const { scrollYProgress: stepsProgress } = useScroll({
    target: stepsRef,
    offset: ["start end", "end start"]
  });

  // Tech stack scale on scroll
  const techScale = useTransform(stepsProgress, [0.3, 0.7], [0.8, 1]);
  const techOpacity = useTransform(stepsProgress, [0.3, 0.7], [0, 1]);

  return (
    <div className="home">
      {/* Hero Section */}
      <motion.section 
        ref={heroRef}
        className="hero"
      >
        <div className="hero-content">
          <motion.h1 
            className="hero-title"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            NBA Proposition Bet Analytics
          </motion.h1>
          <motion.p 
            className="hero-subtitle"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Data-driven insights for smarter and more accurate NBA player proposition betting
          </motion.p>
        </div>

        <div ref={namesRef} className="player-names-section">
          {[row1X, row2X, row3X].map((x, rowIdx) => (
            <motion.div
              key={rowIdx}
              className="player-names-row"
              style={{ x }}
            >
              {[...playerNameRows[rowIdx], ...playerNameRows[rowIdx]].map((name, i) => (
                <span key={i} className="player-name">
                  {name}
                </span>
              ))}
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* How It Works Section */}
      <section ref={stepsRef} className="how-it-works">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Prediction Pipeline
        </motion.h2>

        {/* Horizontal scrolling steps */}
        <div className="steps-container">
          <motion.div 
            className="steps"
          >
            <div className="step">
              <div className="step-text">
                <h3>Fetch Real-time Data</h3>
                <p>
                  We pull the latest NBA player statistics and game logs using the official NBA API,
                  ensuring you have access to the most current player performance data.
                </p>
              </div>
              <div className="step-image">
                <img src={step1Img} alt="Fetch real-time data" />
              </div>
            </div>

            <div className="step">
              <div className="step-text">
                <h3>Get Live Odds</h3>
                <p>
                  Integration with premium odds APIs provides real-time betting lines from multiple
                  bookmakers, giving you the best available lines for each prop.
                </p>
              </div>
              <div className="step-image">
                <img src="https://placehold.co/400x260/1a1a1a/338f4a?text=IMAGE" alt="Get live odds" />
              </div>
            </div>

            <div className="step">
              <div className="step-text">
                <h3>Analyze Patterns</h3>
                <p>
                  Our analyzer calculates confidence scores using hit rate, trend analysis, consistency
                  metrics, and cushion scoring to evaluate each player prop.
                </p>
              </div>
              <div className="step-image">
                <img src="https://placehold.co/400x260/1a1a1a/338f4a?text=IMAGE" alt="Analyze patterns" />
              </div>
            </div>

            <div className="step">
              <div className="step-text">
                <h3>Get Predictions</h3>
                <p>
                  Receive ranked predictions with detailed breakdowns including confidence levels,
                  recent performance trends, and OVER/UNDER recommendations.
                </p>
              </div>
              <div className="step-image">
                <img src="https://placehold.co/400x260/1a1a1a/338f4a?text=IMAGE" alt="Get predictions" />
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Tech Stack Section with scale animation */}
      <motion.section 
        className="tech-stack"
        style={{ scale: techScale, opacity: techOpacity }}
      >
        <h2>Built With</h2>

        <div className="tech-grid">
          <div className="tech-item">
            <h4>Frontend</h4>
            <ul>
              <li>React + TypeScript</li>
              <li>Vite</li>
              <li>Framer Motion</li>
              <li>React Router</li>
            </ul>
          </div>

          <div className="tech-item">
            <h4>Backend</h4>
            <ul>
              <li>Python Flask</li>
              <li>Pandas & NumPy</li>
              <li>NBA API</li>
              <li>The Odds API</li>
            </ul>
          </div>

          <div className="tech-item">
            <h4>Analytics</h4>
            <ul>
              <li>Custom ML Models</li>
              <li>Statistical Analysis</li>
              <li>Trend Detection</li>
              <li>Real-time Caching</li>
            </ul>
          </div>
        </div>
      </motion.section>

      {/* Contact Section */}
      <section className="contact">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          Get In Touch
        </motion.h2>

        <div className="contact-links">
          <motion.a 
            href="https://github.com/Wallfou" 
            target="_blank" 
            rel="noopener noreferrer"
            className="contact-link"
            whileHover={{ scale: 1.1, y: -5 }}
            whileTap={{ scale: 0.95 }}
          >
            <Github size={24} />
            <span>GitHub</span>
          </motion.a>

          <motion.a 
            href="https://linkedin.com/in/yourusername" 
            target="_blank" 
            rel="noopener noreferrer"
            className="contact-link"
            whileHover={{ scale: 1.1, y: -5 }}
            whileTap={{ scale: 0.95 }}
          >
            <Linkedin size={24} />
            <span>LinkedIn</span>
          </motion.a>

          <motion.a 
            href="mailto:your.email@example.com"
            className="contact-link"
            whileHover={{ scale: 1.1, y: -5 }}
            whileTap={{ scale: 0.95 }}
          >
            <Mail size={24} />
            <span>Email</span>
          </motion.a>
        </div>

        <motion.p 
          className="contact-text"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Built by Wa Kenneth Fan • © 2026
        </motion.p>
      </section>
    </div>
  );
};

export default Home;
