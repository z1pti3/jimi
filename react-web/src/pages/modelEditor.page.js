import React, { Component } from "react";

import configData from "../config/config.json";

import "./modelEditor.page.css"

export default class ModelEditor extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="modelEditorFrame" src={configData.url+"model/"}></iframe>
            </div>
        );
    }
}