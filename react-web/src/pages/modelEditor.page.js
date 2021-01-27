import React, { Component } from "react";

import configData from "../config/config.json";
import { URL } from"./../utils/api";

import "./modelEditor.page.css"

export default class ModelEditorPage extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="modelEditorFrame" src={"model/"}></iframe>
            </div>
        );
    }
}