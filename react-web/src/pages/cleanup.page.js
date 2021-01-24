import React, { Component } from "react";

import configData from "../config/config.json";

import "./cleanup.page.css"

export default class CleanupPage extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="cleanupFrame" src={configData.url+"cleanup/"}></iframe>
            </div>
        );
    }
}