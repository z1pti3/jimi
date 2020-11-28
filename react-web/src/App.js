import React from 'react';
import {Container, Row, Col } from "react-bootstrap";

import './app.css';

import PublicRoute from './utils/publicRoute';
import Login from './components/login.component';


import Topbar from './components/topbar.component';
import Sidebar from './components/sidebar.component';
import Tab from './components/tab.component';
 
function App() {
  return (
    <Container fluid>
      <Row>
        <Col>
        <Topbar />
        </Col>
      </Row>
      <Row>

        <Col id="pageContent-wrapper">
          <Tab />
          this is a test
        </Col> 
      </Row>
    </Container>
  );
}
 
export default App;