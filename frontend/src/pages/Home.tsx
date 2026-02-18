import { motion, useScroll, useTransform, useSpring } from 'framer-motion';
import { TrendingUp, BarChart3, Brain, Github, Mail, Linkedin } from 'lucide-react';
import { useRef } from 'react';
import './Home.css';

const Home = () => {
  const heroRef = useRef(null);
  const stepsRef = useRef(null);
  
  // Scroll progress for hero section
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"]
  });

  // Scroll progress for steps section
  const { scrollYProgress: stepsProgress } = useScroll({
    target: stepsRef,
    offset: ["start end", "end start"]
  });

  // Hero parallax effects
  const heroOpacity = useTransform(heroProgress, [0, 0.5], [1, 0]);
  const heroScale = useTransform(heroProgress, [0, 0.5], [1, 0.8]);

  // Stat cards horizontal scroll - moves opposite to page scroll
  const { scrollY } = useScroll();
  const statsX = useTransform(scrollY, [0, 1000], [0, -300]);
  const smoothStatsX = useSpring(statsX, { stiffness: 100, damping: 30 });

  // Steps horizontal scroll - parallax effect
  const stepsX = useTransform(stepsProgress, [0, 1], [-100, 100]);
  const smoothStepsX = useSpring(stepsX, { stiffness: 100, damping: 30 });

  // Tech stack scale on scroll
  const techScale = useTransform(stepsProgress, [0.3, 0.7], [0.8, 1]);
  const techOpacity = useTransform(stepsProgress, [0.3, 0.7], [0, 1]);

  return (
    <div className="home">
      {/* Hero Section */}
      <motion.section 
        ref={heroRef}
        className="hero"
        style={{ opacity: heroOpacity, scale: heroScale }}
      >
        <div className="hero-content">
          <motion.h1 
            className="hero-title"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            NBA Props Predictor
          </motion.h1>
          <motion.p 
            className="hero-subtitle"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Data-driven insights for smarter NBA player prop predictions
          </motion.p>
        </div>
        
        {/* Stat cards with horizontal scroll effect */}
        <div className="hero-stats-container">
          <motion.div
            className="hero-stats"
            style={{ x: smoothStatsX }}
          >
            <div className="stat-card">
              <TrendingUp size={40} />
              <h3>70%+</h3>
              <p>Average Confidence</p>
            </div>
            <div className="stat-card">
              <BarChart3 size={40} />
              <h3>15+</h3>
              <p>Games Analyzed</p>
            </div>
            <div className="stat-card">
              <Brain size={40} />
              <h3>Real-time</h3>
              <p>Live Odds</p>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* How It Works Section */}
      <section ref={stepsRef} className="how-it-works">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          How It Works
        </motion.h2>

        {/* Horizontal scrolling steps */}
        <div className="steps-container">
          <motion.div 
            className="steps"
            style={{ x: smoothStepsX }}
          >
            <div className="step">
              <div className="step-number">1</div>
              <h3>Fetch Real-time Data</h3>
              <p>
                We pull the latest NBA player statistics and game logs using the official NBA API,
                ensuring you have access to the most current player performance data.
              </p>
            </div>

            <div className="step">
              <div className="step-number">2</div>
              <h3>Get Live Odds</h3>
              <p>
                Integration with premium odds APIs provides real-time betting lines from multiple
                bookmakers, giving you the best available lines for each prop.
              </p>
            </div>

            <div className="step">
              <div className="step-number">3</div>
              <h3>Analyze Patterns</h3>
              <p>
                Our analyzer calculates confidence scores using hit rate, trend analysis, consistency
                metrics, and cushion scoring to evaluate each player prop.
              </p>
            </div>

            <div className="step">
              <div className="step-number">4</div>
              <h3>Get Predictions</h3>
              <p>
                Receive ranked predictions with detailed breakdowns including confidence levels,
                recent performance trends, and OVER/UNDER recommendations.
              </p>
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
            href="https://github.com/yourusername" 
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
          transition={{ delay: 0.3, duration: 0.6 }}
        >
          Built by Kenneth Fan • © 2026
        </motion.p>
      </section>
    </div>
  );
};

export default Home;
