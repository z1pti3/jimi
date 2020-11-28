import React from 'react';
import {Container, Row, Col } from "react-bootstrap";

import './app.css';

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
        <Col xs={2} id="sidebar-wrapper">
          <Sidebar />
        </Col>
        <Col xs={10} id="pageContent-wrapper">
          <Tab />
          this
        </Col> 
      </Row>
    </Container>
  );
}
 
export default App;