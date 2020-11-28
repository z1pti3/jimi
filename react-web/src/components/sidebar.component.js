import React from "react";
import {Nav} from "react-bootstrap";

import './sidebar.component.css'

function Sidebar(props) {   
    return (
      <Nav id="sidebar">
        <div class="sidebar-header">
            <h3>Bootstrap Sidebar</h3>
        </div>
        <br/>
        <ul class="list-unstyled components">
            <p>Dummy Heading</p>
            <li>
                <a href="#">Portfolio</a>
            </li>
            <li>
                <a href="#">Contact</a>
            </li>
        </ul>
      </Nav>
    );
  }
   
  export default Sidebar;