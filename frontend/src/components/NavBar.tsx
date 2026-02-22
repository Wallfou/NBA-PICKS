import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import './NavBar.css';

const NavBar = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <motion.nav 
      className="navbar"
      animate={{ y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          <motion.span
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            DraftPicks
          </motion.span>
        </Link>
        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/" className={`nav-link ${isActive('/') ? 'active' : ''}`}>
              <motion.span
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Home
              </motion.span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/picks" className={`nav-link ${isActive('/picks') ? 'active' : ''}`}>
              <motion.span
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Picks
              </motion.span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/players" className={`nav-link ${isActive('/players') ? 'active' : ''}`}>
              <motion.span
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Players
              </motion.span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/games" className={`nav-link ${isActive('/games') ? 'active' : ''}`}>
              <motion.span
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Games
              </motion.span>
            </Link>
          </li>
        </ul>
      </div>
    </motion.nav>
  );
};

export default NavBar;
