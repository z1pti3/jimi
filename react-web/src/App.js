import React from 'react';
import { BrowserRouter, Switch, Route, NavLink } from 'react-router-dom';

import './app.css';

import PrivateRoute from './utils/privateRoute';
import PublicRoute from './utils/publicRoute';
 
import Login from './components/login.component';
import Topbar from './components/topbar.component';
import Sidebar from './components/sidebar.component';
import Home from './home';
 
function App() {
  return (
    <BrowserRouter>
      <Topbar />
      
  </BrowserRouter>
  );
}
 
export default App;